from nmigen import *
from nmigen.build import Platform
from nmigen_library.stream import StreamInterface
from nmigen_library.utils import rising_edge_detected

from nmigen_library.stream.generator import PacketListStreamer

class AudioInit(Elaboratable):
    # MCLK = 12.288MHz
    # PLL Disabled
    # DOSR 128
    # This setup does not work and I don't know why
    init_sequence_dac = [
        [0x30, 0x00, 0x00], # Initialize to Page 0
        [0x30, 0x01, 0x01], # Initialize the device through software reset
        [0x30, 0x04, 0x00], # MCLK pin is CODEC_CLKIN
        [0x30, 0x0b, 0x81], # Power up the NDAC divider with value 1
        [0x30, 0x0c, 0x82], # Power up the MDAC divider with value 2
        [0x30, 0x0d, 0x00], # Program the OSR of DAC to 128
        [0x30, 0x0e, 0x80],
        [0x30, 0x1e, 0x80 + 4],       # BCLK N divider powered up & BCLK N divider = 4
        [0x30, 0x1b, 0b00_11_1_1_00], # I2S, 32bit, BCLK Out, WCLK Out, 00
        #[0x30, 0x1b, 0b0010_0000],    # Set the Audio Interface to I2S 24bits PTM_P4
        [0x30, 0x3c, 0x08],           # Set the DAC Mode to PRB_P8

        [0x30, 0x00, 0x01],          # Select Page 1
        [0x30, 0x01, 0x08],          # Disable weak connection of AVDD with DVDD
        [0x30, 0x02, 0x00],          # Enable Master Analog Power Control
        [0x30, 0x7b, 0x01],          # Set the REF charging time to 40ms

        # Set the Input Common Mode to 0.9V and Output Common Mode for Headphone to
        [0x30, 0x0a, 0x40],          # Full Chip Common Mode is 0.75V
        [0x30, 0x09, 0x0f],          # Power up LOL and LOR drivers
        [0x30, 0x0e, 0x08],          # Route Left DAC to LOL
        [0x30, 0x0f, 0x08],          # Route Right DAC to LOR
        [0x30, 0x03, 0x00],          # Set the DAC PTM mode to PTM_P3/4
        [0x30, 0x04, 0x00],
        [0x30, 0x12, 0x1A],          # Set the LOL gain to 26db
        [0x30, 0x13, 0x1A],          # Set the LOR gain to 26dB

        [0x30, 0x00, 0x00],        # Select Page 0
        # Power up the Left and Right DAC Channels with route the Left Audio digital data to
        [0x30, 0x3f, 0b11_01_01_10], # Left Channel DAC and Right Audio digital data to Right Channel DAC
        [0x30, 0x40, 0x00],          # Unmute the DAC digital volume control
        [0x30, 0x41, 0x1f],          # Left DAC volume control
        [0x30, 0x42, 0x1f],          # Right DAC volume control
    ]

    init_sequence_adc = [
        [0x30, 0x00, 0x00],        # Select Page 0
        [0x30, 0x12, 0x81],        # Power up the NADC divider with value 1
        [0x30, 0x13, 0x82],        # Power up the MADC divider with value 2
        [0x30, 0x14, 0b1000_0000], # Program the OSR of ADC to 128
        [0x30, 0x3d, 0x01],        # Select ADC PRB_R1

        [0x30, 0x00, 0x01],        # Select Page 1
        [0x30, 0x18, 0x05],        # Mixer Amplifier Left Volume Control Volume Control = -2.3dB
        [0x30, 0x19, 0x05],        # Mixer Amplifier Right Volume Control Volume Control = -2.3dB
        [0x30, 0x34, 0x30],        # IN2L is routed to Left MICPGA with 40k resistance
        [0x30, 0x36, 0x31],        # CM is routed to Left MICPGA via CM2L with 10k resistance
        [0x30, 0x37, 0x30],        # IN2R is routed to Right MICPGA with 40k resistance
        [0x30, 0x39, 0x31],        # CM is routed to Right MICPGA via CM2R with 10k resistance

        [0x30, 0x00, 0x00],        # Select Page 0
        [0x30, 0x51, 0xc2],        # Left+Right Channel ADC is powered up & ADC Volume Control Soft-Stepping disabled
        [0x30, 0x52, 0x00],        # Right ADC Channel Un-muted
    ]

    minimal_dac = [
        [0x30, 0x00, 0x00],     # Initialize to Page 0
        [0x30, 0x01, 0x01],     # software reset
        [0x30, 0x04, 0x00],     # MCLK PIN is CODEC_CLKIN
        [0x30, 0x1b, 0b00_11_1_1_00], # I2S, 32bit, BCLK Out, WCLK Out, 00
        [0x30, 0x0b, 0x81],     # Power up the NDAC divider with value 1
        [0x30, 0x0c, 0x82],     # Power up the MDAC divider with value 2
        [0x30, 0x0d, 0x00],     # Program the OSR of DAC to 128
        [0x30, 0x0e, 0x80],
        [0x30, 0x1e, 0x80 + 4], # BCLK N divider powered up & BCLK N divider = 4
        [0x30, 0x3c, 0x19],     #Set the DAC Mode to PRB_P25
        [0x30, 0x3f, 0xd4],     #Power up the Left and Right DAC

        [0x30, 0x00, 0x01],     # page1
        [0x30, 0x09, 0x0f],     # Power up LOL and LOR drivers
        [0x30, 0x0e, 0x08],     # Left DAC----LOL
        [0x30, 0x0f, 0x08],     # Right DAC---LOR
        [0x30, 0x12, 0x08],     # LOL driver gain is 8dB
        [0x30, 0x13, 0x08],     # LOR driver gain is 8dB
        [0x30, 0x01, 0x08],     # Disabled weak connection of AVDD with DVDD
        [0x30, 0x02, 0x01],     # Eabled Master Analog Power Control
        [0x30, 0x7b, 0x01],     # /Set the REF charding time to 40ms
        [0x30, 0x0a, 0x40],     # Full Chip Common Mode is 0.75V

        [0x30, 0x00, 0x00],     # page0
        [0x30, 0x40, 0x00],     # Unmute the DAC digital volume control
        [0x30, 0x41, 0x00],     # Left DAC volume control  0.0db
        [0x30, 0x42, 0x00],     # Right DAC volume control  0.0db
        [0x30, 0x44, 0x7f],     # Enable DRC
        [0x30, 0x45, 0x00],     # DRC Hold Disabled
        [0x30, 0x46, 0xe2],     #
    ]

    # use this with minimal_dac for a beep test
    beep_test = [
        [0x30, 0x49, 0xff],  #beep reg3
        [0x30, 0x4a, 0xff],  #beep reg4
        [0x30, 0x4b, 0xff],  #beep reg5
        [0x30, 0x4c, 0x21],  #beep reg6
        [0x30, 0x4d, 0x21],  #beep reg7
        [0x30, 0x4e, 0x7b],  #beep reg8
        [0x30, 0x4f, 0xa3],  #beep reg9
        [0x30, 0x48, 0x04],  #beep reg2
        [0x30, 0x47, 0x84],  #enable, beep generator
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
            PacketListStreamer(self.minimal_dac + self.init_sequence_adc)

        m.d.comb += [
            init_streamer.start.eq(rising_edge_detected(m, self.start, domain="usb")),
            self.stream_out.stream_eq(init_streamer.stream),
        ]

        with m.If(init_streamer.done):
            m.d.usb += self.done.eq(1)

        return m