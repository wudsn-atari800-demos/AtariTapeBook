# Atari Tape Book

The Atari Tape Books is a software for Atari 8-bit computer with at least 16k of RAM (Atari 400/800/XL/XE).

## Tape Format
The software is provide as a stereo tape in ".wav" format with 44.1kHz sample rate and 16-bit resolution.
The left channel contains the audio-track, the right channel contain the data track with standard 600 baud data rate.
The data track contains a short boot loader, to allow booting with the `START` key held during power-up.
The bool loader is followed by a chain for Atari BASIC programs saved in `CSAVE` format with short inter-recording gaps (IRG).
The short IRGs reducde the loading time.

## Folders
The chapters of the book are stored in the `chapters` folder.
For every chapter there is a `C<n>.BAS` file in tokenized Atari BASIC format and a `C<n>.WAV` file wich can be in mono or stereo format.
The build process automatically converts the `C<n>.WAV` file to a mono track in the output format of the tape.


## Build Tools
The build is started with `Makefile.bat` and requires the following tools.

| Tool | Version | Download | Purpose |
|------|---------|----------|---------|
| MADS | 2.1.7 | [Mad-Assembler](https://github.com/tebe6502/Mad-Assembler) | Assembles `boot/Boot.asm` to `boot/Boot.sec`. |
| Python | 3.9 or later | [python.org](https://www.python.org/downloads/) | Runs `Bin2Wav.py`, which builds the tape. Only the standard library is used. |
| Java | 21 | [Adoptium](https://adoptium.net/) | Runs TURGEN. |
| TURGEN | 9.4.7 | [TURGEN](https://turgen.sourceforge.io/) | Its GENCAS tool converts the boot file and the BASIC programs to 600 baud tape records. |
| AltirraBridge | nightly | [AltirraSDL releases](https://github.com/ilmenit/AltirraSDL/releases/tag/nightly-bridge) | Headless Altirra that boots the new tape and checks the boot file. |
| Altirra | 4.50 | [Altirra](https://www.virtualdub.org/altirra.html) | Plays the tape after the build and is used to edit the BASIC programs. |

The tools are added as follows.
- Each tool is installed or unpacked into a folder of its own. TURGEN and AltirraBridge stay in their unpacked folder structure, because `Bin2Wav.py` loads `dist/turgen.jar` and the AltirraBridge Python SDK from there.
- For AltirraBridge, the `AltirraBridge-<version>-windows-x86_64` package from the release page is used. Its Python SDK does not have to be installed with `pip`.
- The folders of the tools are entered in `Make-Settings.bat`. It adds them to the `PATH`, and `Makefile.bat` and `Altirra.bat` call it first. It is the only file with machine-specific folders.
- Python is expected in the `PATH` already. Tools that are already in the `PATH` can be left out of `Make-Settings.bat`.

## Editing
The Atari BASIC files can be editing in Altirra by starting the "Altirra.bat" script followed by `LOAD "H:C1.BAS"`to load the program.
