# Atari Tape Book

The Atari Tape Books is a software for Atari 8-bit computer with at least 16k of RAM (Atari 400/800/XL/XE).

The content language is German. Maybe English will be added later.

## Tape Format
The software is provide as a stereo tape in ".wav" format with 44.1kHz sample rate and 16-bit resolution.
The left channel contains the audio-track, the right channel contain the data track with standard 600 baud data rate.
The data track contains a short boot loader, to allow booting with the `START` key held during power-up.
The bool loader is followed by a chain for Atari BASIC programs saved in `CSAVE` format with short inter-recording gaps (IRG).
The short IRGs reducde the loading time.

## Folders
The chapters of the book are stored in the `chapters` folder.
The tape consists of sections, which `Makefile.bat` lists in tape order by their base name, for example `chapters/C1`.
The files with that base name decide the type of a section:

| Files | Section type |
|-------|--------------|
| `.BAS`, optionally `.WAV` | Load section. The tokenized Atari BASIC program is loaded with `CLOAD`, and the audio plays while it loads. |
| `.WAV`, optionally `.TXT` | Run section. The audio plays while the loaded program runs, after a lead-in of one second while the motor spins up. |

The `.WAV` files can be in mono or stereo format. The build process converts them to a mono track in the output format of the tape.
The `.TXT` file of a run section contains cue points for the audio, exported from an Audacity label track.
For every cue point, the build writes a sync pulse on the data track, which the program can read from `SKSTAT` to keep the screen in step with the speech, see `test/Conversational-German/ANALYSIS.md`.
A load section cannot have a `.TXT` file.


## Build Tools
The build is started with `Makefile.bat` and requires the following tools.

| Tool | Version | Download | Purpose |
|------|---------|----------|---------|
| Python | 3.9 or later | [python.org](https://www.python.org/downloads/) | Runs `Bin2Wav.py`, which builds the tape. Only the standard library is used. |
| MADS | latest | [WUDSN IDE Tools](https://github.com/wudsn/wudsn-ide-tools) | Assembles `boot/Boot.asm` to `boot/Boot.sec`. |
| Java | 21, latest update | [Adoptium](https://adoptium.net/) | Runs TURGEN. |
| TURGEN | latest | [TURGEN](https://turgen.sourceforge.io/) | Its GENCAS tool converts the boot file and the BASIC programs to 600 baud tape records. |
| AltirraBridge | nightly | [AltirraSDL releases](https://github.com/ilmenit/AltirraSDL/releases/tag/nightly-bridge) | Headless Altirra that boots the new tape and checks the boot file. |
| Altirra | 4.40 | [Altirra](https://www.virtualdub.org/altirra.html) | Plays the tape after the build and is used to edit the BASIC programs. |
| A8CAS | 1.3.1 | [A8CAS](https://a8cas.sourceforge.net/) | Converts cassette recordings to `.cas` tape images, used by the scripts in the `test` folder. |

Python is installed globally, for example with the installer from python.org or with `winget install Python.Python.3.13`.
All other tools are downloaded by `Make-Setup.bat` into the `build` folder, which is not part of the repository.
Run it once before the first build. Tools that are already there are kept, so delete a tool's folder in `build` to get its latest version.
`Make-Settings.bat` adds the folders in `build` to the `PATH`. `Makefile.bat` and `Altirra.bat` call it first.

The downloaded Altirra starts with its built-in AltirraOS and Altirra BASIC.
To use the original Atari OS and Atari BASIC, register your own ROM images in Altirra under System, Firmware.

## Editing
The Atari BASIC files can be editing in Altirra by starting the "Altirra.bat" script followed by `LOAD "H:C1.BAS"`to load the program.

## Project Members

- Prof. Dr. Stefan Höltgen
- Dr. Torsten Roeder
- Stefan Meyer
- Andreas Kahlenbach
- Peter Dell


