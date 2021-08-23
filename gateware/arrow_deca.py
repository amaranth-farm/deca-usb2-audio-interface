import os
import subprocess

from nmigen import *
from nmigen.build import *
from nmigen.vendor.intel import *
from nmigen_boards.resources import *

from luna.gateware.platform.core import LUNAPlatform, NullPin

__all__ = ["ArrowDECAPlatform"]

class ArrowDECAClockAndResetController(Elaboratable):
    """ Controller for clocking and global resets. """
    def __init__(self, *, clock_frequencies=None, clock_signal_name=None):
        pass

    def elaborate(self, platform):
        m = Module()

        # Create our domains; but don't do anything else for them, for now.
        m.domains.sync = ClockDomain()
        m.domains.usb  = ClockDomain()
        m.domains.fast = ClockDomain()

        clocks = Signal(2)
        locked = Signal()

        m.submodules.pll = Instance("ALTPLL",
            p_BANDWIDTH_TYPE         = "AUTO",
            p_CLK0_DIVIDE_BY         = 1,
            p_CLK0_DUTY_CYCLE        = 50,
            p_CLK0_MULTIPLY_BY       = 1,
            p_CLK0_PHASE_SHIFT       = -5556,
            p_INCLK0_INPUT_FREQUENCY = 16666,
            p_COMPENSATE_CLOCK       = "CLK0",
            p_INTENDED_DEVICE_FAMILY = "MAX 10",
            p_CLK1_DIVIDE_BY         = 1,
            p_CLK1_DUTY_CYCLE        = 50,
            p_CLK1_MULTIPLY_BY       = 2,
            p_CLK1_PHASE_SHIFT       = 0,
            p_OPERATION_MODE         = "NORMAL",

            # Drive our clock from the USB clock
            # coming from the USB clock pin of the USB3300
            i_inclk  = platform.request("clk60"),
            o_clk    = clocks,
            o_locked = locked,
        )

        m.d.comb += [
            ClockSignal("usb") .eq(clocks[0]),
            ClockSignal("sync").eq(ClockSignal("usb")),
            ClockSignal("fast").eq(clocks[1]),
        ]

        # Use a blinky to see if the clock signal works
        # from nmigen_boards.test.blinky import Blinky
        # m.submodules += Blinky()

        usb = platform.request("usb")
        m.d.comb += [
            usb.cs.eq(1),
        ]

        return m

class ArrowDECAPlatform(IntelPlatform, LUNAPlatform):
    device      = "10M50DA" # MAX 10
    package     = "F484"
    speed       = "C6"
    suffix      = "GES"
    default_clk = "clk50"

    clock_domain_generator = ArrowDECAClockAndResetController
    default_usb_connection = "ulpi"
    ignore_phy_vbus = True

    resources   = [
        Resource("clk50", 0, Pins("M8", dir="i"),
            Clock(50e6), Attrs(io_standard="2.5 V")),
        Resource("clk50", 1, Pins("P11", dir="i"),
            Clock(50e6), Attrs(io_standard="3.3 V")),
        Resource("clk50", 2, Pins("N15", dir="i"),
            Clock(50e6), Attrs(io_standard="1.5 V")),
        Resource("clk10", 0, Pins("M9", dir="i"),
            Clock(10e6), Attrs(io_standard="2.5 V")),

        *LEDResources(
            pins="C7 C8 A6 B7 C4 A5 B4 C5",
            invert=True,
            attrs=Attrs(io_standard="1.2 V")),
        *ButtonResources(
            pins="H21 H22",
            invert=True,
            attrs=Attrs(io_standard="1.5 V")),
        *SwitchResources(
            pins="J21 J22",
            attrs=Attrs(io_standard="1.5 V")),

        Resource("clk60", 0, Pins("H11", dir="i"), Clock(60e6), Attrs(io_standard="1.2 V")),
        Resource("usb", 0, Subsignal("fault", Pins("D8",  dir="i", invert=True),  Attrs(io_standard="1.2 V")),
                           Subsignal("cs",    Pins("J11", dir="o", invert=False), Attrs(io_standard="1.8 V"))),

        Resource("ulpi", 0,
            Subsignal("clk",     Pins("W3", dir="o"),  Attrs(io_standard="3.3-V LVCMOS")),
            Subsignal("stp",     Pins("J12", dir="o"), Attrs(io_standard="1.8 V")),
            Subsignal("dir",     Pins("J13", dir="i"), Attrs(io_standard="1.8 V")),
            Subsignal("nxt",     Pins("H12", dir="i"), Attrs(io_standard="1.8 V")),
            Subsignal("reset",   Pins("E16", dir="o", invert=True), Attrs(io_standard="1.8 V")),
            Subsignal("data",    Pins("E12 E13 H13 E14 H14 D15 E15 F15", dir="io"), Attrs(io_standard="1.8 V")),
        ),

        # use this to debug i2c with a logic analyzer
        # I2CResource("i2c_audio", 0, sda="P_8:3", scl="P_8:5", attrs=Attrs(io_standard="3.3-V LVCMOS", WEAK_PULL_UP_RESISTOR="ON")),

        I2CResource("i2c_audio", 0, sda="P21", scl="P20", attrs=Attrs(io_standard="1.5 V")),

        SPIResource("spi_audio", 0, cs_n="P20", clk="P19", copi="P21", cipo="N21", attrs=Attrs(io_standard="1.5 V")),

        # debug i2s with external logic analyzer
        Resource("debug", 0,
            Subsignal("bclk", Pins("P_8:3", dir="o")),
            Subsignal("wclk", Pins("P_8:5", dir="o")),
            Subsignal("adc",  Pins("P_8:7", dir="o")),
            Subsignal("dac",  Pins("P_8:9", dir="o")),
            Attrs(io_standard="3.3-V LVCMOS")
        ),

        Resource("audio", 0,
            Subsignal("reset",      PinsN("M21", dir="o")),
            Subsignal("mclk",       Pins ("P14", dir="o")),
            Subsignal("wclk",       Pins ("R15", dir="i")),
            Subsignal("bclk",       Pins ("R14", dir="i")),
            Subsignal("spi_select", Pins ("N22", dir="o")),
            Subsignal("din_mfp1",   Pins ("P15", dir="o")),
            Subsignal("dout_mfp2",  Pins ("P18", dir="i")),
            Subsignal("sclk_mfp3",  Pins ("P19", dir="o")),
            Subsignal("miso_mfp4",  Pins ("N21", dir="i")),
            Subsignal("gpio_mfp5",  Pins ("M22", dir="o")),
            Attrs(io_standard="1.5 V")
        ),
    ]

    connectors  = [
        Connector("gpio", 0,
            "W18  Y18  Y19  AA17 AA20 AA19 AB21 AB20 AB19 Y16  V16  "
            "AB18 V15  W17  AB17 AA16 AB16 W16  AB15 W15  Y14  AA15 "
            "AB14 AA14 AB13 AA13 AB12 AA12 AB11 AA11 AB10 Y13  Y11  "
            "W13  W12  W11  V12  V11  V13  V14  Y17  W14  U15  R13"),

        Connector("gpio", 1,
            "Y5   Y6   W6   W7   W8   V8   AB8   V7  R11  AB7  AB6  "
            "AA7  AA6  Y7   V10  U7   W9   W5   R9   W4    P9  V17  "
            "W3"),

        Connector("P", 8, {
            "3":  "W18",   "4": "Y18",
            "5":  "Y19",   "6": "AA17",
            "7":  "AA20",  "8": "AA19",
            "9":  "AB21", "10": "AB20",
            "11": "AB19", "12": "Y16",
            "13": "V16",  "14": "AB18",
            "15": "V15",  "16": "W17",
            "17": "AB17", "18": "AA16",
            "19": "AB16", "20": "W16",
            "21": "AB15", "22": "W15",
            "23": "Y14",  "24": "AA15",
            "25": "AB14", "26": "AA14",
            "27": "AB13", "28": "AA13",
            "29": "AB12", "30": "AA12",
            "31": "AB11", "32": "AA11",
            "33": "AB10", "34": "Y13",
            "35": "Y11",  "36": "W13",
            "37": "W12",  "38": "W11",
            "39": "V12",  "40": "V11",
            "41": "V13",  "42": "V14",
            "43": "Y17",  "44": "W14",
            "45": "U15",  "46": "R13",}),

        Connector("P", 9, {
            "11": "Y5",  "12": "Y6",
            "13": "W6",  "14": "W7",
            "15": "W8",  "16": "V8",
            "17": "B8",  "18": "V7",
            "19": "R11", "20": "AB7",
            "21": "AB6", "22": "AA7",
            "23": "AA6", "24": "Y7",
            "25": "V10", "26": "U7",
            "27": "W9",  "28": "W5",
            "29": "R9",  "30": "W4",
            "31": "P9",
            "41": "V17", "42": "W3"}),
    ]

    def toolchain_program(self, products, name):
        quartus_pgm = os.environ.get("QUARTUS_PGM", "quartus_pgm")
        with products.extract("{}.sof".format(name)) as bitstream_filename:
            subprocess.check_call([quartus_pgm, "--haltcc", "--mode", "JTAG",
                                   "--operation", "P;" + bitstream_filename])

    @property
    def file_templates(self):
        # Configure the voltages of the I/O banks by appending the global
        # assignments to the template. However, we create our own copy of the
        # file templates before modifying them to avoid modifying the original.
        return {
            **super().file_templates,
            "{{name}}.qsf":
                super().file_templates.get("{{name}}.qsf") +
                r"""
                set_global_assignment -name IOBANK_VCCIO 2.5V -section_id 1A
                set_global_assignment -name IOBANK_VCCIO 2.5V -section_id 1B
                set_global_assignment -name IOBANK_VCCIO 2.5V -section_id 2
                set_global_assignment -name IOBANK_VCCIO 3.3V -section_id 3
                set_global_assignment -name IOBANK_VCCIO 3.3V -section_id 4 # P8
                set_global_assignment -name IOBANK_VCCIO 1.5V -section_id 5
                set_global_assignment -name IOBANK_VCCIO 1.5V -section_id 6
                set_global_assignment -name IOBANK_VCCIO 1.8V -section_id 7
                set_global_assignment -name IOBANK_VCCIO 1.2V -section_id 8

                set_global_assignment -name FORCE_CONFIGURATION_VCCIO ON
                set_global_assignment -name AUTO_RESTART_CONFIGURATION OFF
                set_global_assignment -name ENABLE_CONFIGURATION_PINS OFF
                set_global_assignment -name ENABLE_BOOT_SEL_PIN OFF
                set_global_assignment -name INTERNAL_FLASH_UPDATE_MODE \"SINGLE IMAGE WITH ERAM\"
                """
        }
