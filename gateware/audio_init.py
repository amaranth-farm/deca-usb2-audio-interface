from nmigen import *
from nmigen.build import Platform
from nmigen_library.stream import StreamInterface

from nmigen_library.stream.generator import PacketListStreamer

class AudioInit(Elaboratable):
    # Assumption
    # AVdd = 1.8V, DVdd = 1.8V
    # MCLK = 12.288MHz
    # Ext C = 47uF
    # Based on C the wait time will change.
    # Wait time = N*Rpop*C + 4* Offset ramp time
    # Default settings used.
    # PLL Disabled
    # DOSR 128
    init_sequence = [
        # Initialize to Page 0
        [0x30, 0x00, 0x00],
        # Initialize the device through software reset
        [0x30, 0x01, 0x01],
        # Power up the NDAC divider with value 1
        [0x30, 0x0b, 0x81],
        # Power up the MDAC divider with value 2
        [0x30, 0x0c, 0x82],
        # Program the OSR of DAC to 128
        [0x30, 0x0d, 0x00],
        [0x30, 0x0e, 0x80],
        # Set the word length of Audio Interface to 20bits PTM_P4
        [0x30, 0x1b, 0x10],
        # Set the DAC Mode to PRB_P8
        [0x30, 0x3c, 0x08],
        # Select Page 1
        [0x30, 0x00, 0x01],
        # Disable Internal Crude AVdd in presence of external AVdd supply or before
        #powering up internal AVdd LDO
        [0x30, 0x01, 0x08],
        # Enable Master Analog Power Control
        [0x30, 0x02, 0x00],
        # Set the REF charging time to 40ms
        [0x30, 0x7b, 0x01],
        # HP soft stepping settings for optimal pop performance at power up
        # Rpop used is 6k with N = 6 and soft step = 20usec. This should work with 47uF coupling
        # capacitor. Can try N=5,6 or 7 time constants as well. Trade-off delay vs “pop” sound.
        [0x30, 0x14, 0x25],
        # Set the Input Common Mode to 0.9V and Output Common Mode for Headphone to
        # Input Common Mode
        [0x30, 0x0a, 0x00],
        # Route Left DAC to HPL
        [0x30, 0x0c, 0x08],
        # Route Right DAC to HPR
        [0x30, 0x0d, 0x08],
        # Set the DAC PTM mode to PTM_P3/4
        [0x30, 0x03, 0x00],
        [0x30, 0x04, 0x00],
        # Set the HPL gain to 0dB
        [0x30, 0x10, 0x00],
        # Set the HPR gain to 0dB
        [0x30, 0x11, 0x00],
        # Power up HPL and HPR drivers
        [0x30, 0x09, 0x30],
        # Wait for 2.5 sec for soft stepping to take effect
        # Else read Page 1, Register 63d, D(7:6). When = “11” soft-stepping is complete
        # Select Page 0
        [0x30, 0x00, 0x00],
        # Power up the Left and Right DAC Channels with route the Left Audio digital data to
        # Left Channel DAC and Right Audio digital data to Right Channel DAC
        [0x30, 0x3f, 0xd6],
        # Unmute the DAC digital volume control
        [0x30, 0x40, 0x00],
    ]

    def __init__(self) -> None:
        self.start      = Signal()
        self.done       = Signal()
        self.stream_out = StreamInterface()

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        m.domains += ClockDomain("audio")

        audio_locked = Signal()

        m.submodules.audio_pll = Instance("ALTPLL",
            p_BANDWIDTH_TYPE         = "AUTO",
            # ADAT clock = 12.288 MHz = 48 kHz * 256
            p_CLK0_DIVIDE_BY         = 83,
            p_CLK0_DUTY_CYCLE        = 50,
            p_CLK0_MULTIPLY_BY       = 17,
            p_CLK0_PHASE_SHIFT       = 0,

            p_INCLK0_INPUT_FREQUENCY = 16667,
            p_OPERATION_MODE         = "NORMAL",

            i_inclk  = ClockSignal("usb"),
            o_clk    = ClockSignal("audio"),
            o_locked = audio_locked,
        )

        m.d.comb += ResetSignal("audio").eq(~audio_locked)

        m.submodules.audio_init_streamer = init_streamer = \
            PacketListStreamer(self.init_sequence)

        m.d.comb += init_streamer.start.eq(self.start)
        with m.If(init_streamer.done):
            m.d.sync += self.done.eq(1)

        return m