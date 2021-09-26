# DECA USB Audio Interface

DECA based USB 2.0 High Speed audio interface

## Status / current limitations
* enumerates as class compliant audio device on Linux and Windows.
* Works on the FPGA
* Playback works
* Recording works
* only 48kHz sample rate supported
* integrated USB2 high speed logic analyzer works

## support
In the release section I provide a .sof file (for directly programming the board)
and a .pof file (for flashing the device), for convenience.
Saves you from building the project yourself, if you do not want to.

If you encounter issues building this project, I recommend reading this article:
[http://retroramblings.net/?p=1718](http://retroramblings.net/?p=1718)
