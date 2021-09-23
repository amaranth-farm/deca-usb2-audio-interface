from nmigen import *
from nmigen.build import *

from nmigen_boards.resources import *
from nmigen_boards.qmtech_10cl006 import QMTech10CL006Platform

from luna.gateware.platform.core import LUNAPlatform

class USBSoundCardClockDomainGenerator(Elaboratable):
    def __init__(self, *, clock_frequencies=None, clock_signal_name=None):
        pass

    def elaborate(self, platform):
        m = Module()

        # Create our domains
        m.domains.usb   = ClockDomain("usb")
        m.domains.sync  = ClockDomain("sync")
        m.domains.fast  = ClockDomain("fast")
        m.domains.sound = ClockDomain("sound")

        clk = platform.request(platform.default_clk)

        sys_clocks   = Signal(3)
        sound_clocks = Signal(2)

        sys_locked   = Signal()
        sound_locked = Signal()
        reset       = Signal()

        m.submodules.mainpll = Instance("ALTPLL",
            p_BANDWIDTH_TYPE         = "AUTO",
            # 100MHz
            p_CLK0_DIVIDE_BY         = 1,
            p_CLK0_DUTY_CYCLE        = 50,
            p_CLK0_MULTIPLY_BY       = 2,
            p_CLK0_PHASE_SHIFT       = 0,
            # 60MHz
            p_CLK1_DIVIDE_BY         = 5,
            p_CLK1_DUTY_CYCLE        = 50,
            p_CLK1_MULTIPLY_BY       = 6,
            p_CLK1_PHASE_SHIFT       = 0,

            p_INCLK0_INPUT_FREQUENCY = 20000,
            p_OPERATION_MODE         = "NORMAL",

            # Drive our clock from the USB clock
            # coming from the USB clock pin of the USB3300
            i_inclk  = clk,
            o_clk    = sys_clocks,
            o_locked = sys_locked,
        )

        sound_locked = Signal()
        m.submodules.soundpll = Instance("ALTPLL",
            p_BANDWIDTH_TYPE         = "AUTO",
            # sound clock = 3.072 MHz = 48 kHz * 32 bit * 2 channels
            p_CLK0_DIVIDE_BY         = 83 * 4,
            p_CLK0_DUTY_CYCLE        = 50,
            p_CLK0_MULTIPLY_BY       = 17,
            p_CLK0_PHASE_SHIFT       = 0,

            p_INCLK0_INPUT_FREQUENCY = 16667,
            p_OPERATION_MODE         = "NORMAL",

            i_inclk  = sys_clocks[1],
            o_clk    = sound_clocks,
            o_locked = sound_locked,
        )

        m.d.comb += [
            reset.eq(~(sys_locked & sound_locked)),
            ClockSignal("fast").eq(sys_clocks[0]),
            ClockSignal("usb") .eq(sys_clocks[1]),
            ClockSignal("sync").eq(sys_clocks[1]),
            ClockSignal("sound").eq(sound_clocks[0]),
            ResetSignal("fast").eq(reset),
            ResetSignal("usb") .eq(reset),
            ResetSignal("sync").eq(reset),
            ResetSignal("sound").eq(reset),
        ]

        return m

class USBSoundCardPlatform(QMTech10CL006Platform, LUNAPlatform):
    clock_domain_generator = USBSoundCardClockDomainGenerator
    default_usb_connection = "ulpi"
    number_of_channels     = 8
    bitwidth               = 24

    @property
    def file_templates(self):
        templates = super().file_templates
        templates["{{name}}.qsf"] += r"""
            set_global_assignment -name OPTIMIZATION_MODE "Aggressive Performance"
            #set_global_assignment -name FITTER_EFFORT "Standard Fit"
            set_global_assignment -name PHYSICAL_SYNTHESIS_EFFORT "Extra"
            set_instance_assignment -name DECREASE_INPUT_DELAY_TO_INPUT_REGISTER OFF -to *ulpi*
            set_instance_assignment -name INCREASE_DELAY_TO_OUTPUT_PIN OFF -to *ulpi*
            set_global_assignment -name NUM_PARALLEL_PROCESSORS ALL
        """
        templates["{{name}}.sdc"] += r"""
            derive_pll_clocks
            """
        return templates

    def __init__(self):
        self.resources += [
            # USB2 / ULPI section of the USB3300.
            ULPIResource("ulpi", 0,
                data="J_2:17 J_2:19 J_2:21 J_2:23 J_2:18 J_2:20 J_2:22 J_2:24",
                clk="J_2:7", clk_dir="o", # this needs to be a clock pin of the FPGA or the core won't work
                dir="J_2:11", nxt="J_2:13", stp="J_2:9", rst="J_2:8", rst_invert=True, # USB3320 reset is active low
                attrs=Attrs(io_standard="3.3-V LVCMOS")),

            Resource("debug_led", 0, PinsN("J_2:39 J_2:38 J_2:37 J_2:36", dir="o"),
                Attrs(io_standard="3.3-V LVCMOS")),

            Resource("i2s", 0,
                Subsignal("data",  Pins("J_2:51", dir="o")),
                Subsignal("bclk",  Pins("J_2:53", dir="o")),
                Subsignal("wclk",  Pins("J_2:55", dir="o")),
                Attrs(io_standard="3.3-V LVCMOS"))
        ]

        super().__init__(standalone=False)