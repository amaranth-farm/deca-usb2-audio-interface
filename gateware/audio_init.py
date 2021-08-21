from nmigen import *
from nmigen.build import Platform
from nmigen_library.stream import StreamInterface
from nmigen_library.utils import rising_edge_detected

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
        [0x31, 0x00, 0x00],
        # Initialize the device through software reset
        [0x31, 0x01, 0x01],
        # Power up the NDAC divider with value 1
        [0x31, 0x0b, 0x81],
        # Power up the MDAC divider with value 2
        [0x31, 0x0c, 0x82],
        # Program the OSR of DAC to 128
        [0x31, 0x0d, 0x00],
        [0x31, 0x0e, 0x80],
        # Set the Audio Interface to I2S 24bits PTM_P4
        [0x31, 0x1b, 0b0010_0000],
        # Set the DAC Mode to PRB_P8
        [0x31, 0x3c, 0x08],

        # Select Page 1
        [0x31, 0x00, 0x01],
        # Enable Internal Crude AVdd because AVDD it is not connected
        [0x31, 0x01, 0x00],
        # Enable Master Analog Power Control
        [0x31, 0x02, 0x00],
        # Set the REF charging time to 40ms
        [0x31, 0x7b, 0x01],
        # Set the Input Common Mode to 0.9V and Output Common Mode for Headphone to
        # Input Common Mode
        [0x31, 0x0a, 0x00],
        # Route Left DAC to LOL
        [0x31, 0x0e, 0x08],
        # Route Right DAC to LOR
        [0x31, 0x0f, 0x08],
        # Set the DAC PTM mode to PTM_P3/4
        [0x31, 0x03, 0x00],
        [0x31, 0x04, 0x00],
        # Set the LOL gain to 0dB
        [0x31, 0x12, 0x00],
        # Set the LOR gain to 0dB
        [0x31, 0x13, 0x00],
        # Power up LOL and LOR drivers
        [0x31, 0x09, 0b0000_1100],

        # Select Page 0
        [0x31, 0x00, 0x00],
        # Power up the Left and Right DAC Channels with route the Left Audio digital data to
        # Left Channel DAC and Right Audio digital data to Right Channel DAC
        [0x31, 0x3f, 0b11_01_01_10],
        # Unmute the DAC digital volume control
        [0x31, 0x40, 0x00],
    ]

    beep_test = [
        [0x31, 0x00, 0x00], # Initialize to Page 0
        [0x31, 0x01, 0x01], #software reset
        [0x31, 0x04, 0x00], #MCLK PIN is CODEC_CLKIN
        [0x31, 0x1B, 0x0D], #BCLK is output from the device & WCLK is output from the device & DOUT will be high impedance after data has been transferred
        [0x31, 0x0b, 0x81], #NDAC divider power up / NDAC=1
        [0x31, 0x0C, 0x82], #MDAC divider power up / MDAC=2
        [0x31, 0x0D, 0x00], #DOSR MSB
        [0x31, 0x0E, 0x80], #DOSR LSB  / DOSR=128
        [0x31, 0x1E, 0x90], #BCLK N divider powered up & BCLK N divider = 128
        [0x31, 0x3c, 0x19], #Set the DAC Mode to PRB_P25
        [0x31, 0x3f, 0xd4], #Power up the Left and Right DAC
        [0x31, 0x00, 0x01], #page1
        [0x31, 0x09, 0x0f], #Power up LOL and LOR drivers
        [0x31, 0x0e, 0x08], #Left DAC----LOL
        [0x31, 0x0f, 0x08], #Right DAC---LOR
        [0x31, 0x12, 0x08], #LOL driver gain is 8dB
        [0x31, 0x13, 0x08], #LOR driver gain is 8dB
        [0x31, 0x01, 0x08], #Disabled weak connection of AVDD with DVDD
        [0x31, 0x02, 0x01], #Eabled Master Analog Power Control
        [0x31, 0x7b, 0x01], #/Set the REF charding time to 40ms
        [0x31, 0x0a, 0x40], #Full Chip Common Mode is 0.75V
        [0x31, 0x00, 0x00], #page0
        [0x31, 0x40, 0x00], #Unmute the DAC digital volume control

        [0x31, 0x41, 0x00],  #Left DAC volume control  0.0db
        [0x31, 0x42, 0x00],  #Right DAC volume control  0.0db
        [0x31, 0x44, 0x7f],  #Enable DRC
        [0x31, 0x45, 0x00],  #DRC Hold Disabled
        [0x31, 0x46, 0xe2],  #
        [0x31, 0x49, 0xff],  #beep reg3
        [0x31, 0x4a, 0xff],  #beep reg4
        [0x31, 0x4b, 0xff],  #beep reg5
        [0x31, 0x4c, 0x21],  #beep reg6
        [0x31, 0x4d, 0x21],  #beep reg7
        [0x31, 0x4e, 0x7b],  #beep reg8
        [0x31, 0x4f, 0xa3],  #beep reg9
        [0x31, 0x48, 0x04],  #beep reg2
        [0x31, 0x47, 0x84],  #enable, beep generator
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
            PacketListStreamer(self.beep_test)

        m.d.comb += [
            init_streamer.start.eq(rising_edge_detected(m, self.start, domain="usb")),
            self.stream_out.stream_eq(init_streamer.stream),
        ]

        with m.If(init_streamer.done):
            m.d.sync += self.done.eq(1)

        return m