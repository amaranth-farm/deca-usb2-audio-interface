# DECA USB Audio Interface

DECA based USB 2.0 High Speed audio interface

## Status / current limitations
* enumerates as class compliant audio device on Linux and Windows.
* Works on the FPGA, DAC chip output sound
* only 48kHz sample rate supported
* audio input is still a dummy. The ADC still needs to be hooked up,
  and an I2S receiver core is missing
* integrated USB2 high speed logic analyzer works
