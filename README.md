# Atari Tape Book

The Atari Tape Books is a software for Atari 8-bit computer with at least 16k of RAM (Atari 400/800/XL/XE).

The content language is German. Maybe English will be added later.

## Tape Format
The software is provide as a stereo tape in ".wav" format with 44.1kHz sample rate and 16-bit resolution.
The left channel contains the audio-track, the right channel contain the data track with standard 600 baud data rate.
The data track contains a short boot loader, to allow booting with the `START` key held during power-up.
The boot loader fades the boot screen to black, types the title and `LOADING`, and then loads the animated cassette intro from the `intro` folder, which is shown while the tape loads, see `plans/01_INTRO_DURING_LOADING_PLAN.md` and `plans/03_BOOT_FADE_AND_TEXT_PLAN.md`.
The intro and the BASIC services are stored ZX0-compressed and decompressed record by record while they load (`zx0/Zx0.asm`), see `plans/08_ZX0_INTRO_PLAN.md`.
While the intro loads, a narrator speaks on the audio track, from the moment the loading continues after the title. The text is in `boot/Narration.txt`; `Makefile.bat` speaks it into `boot/Boot.WAV` with the Windows speech synthesizer if that file is missing, and `boot/Make-Narration.bat` speaks it again after the text changed. A recording can replace `boot/Boot.WAV`. `Bin2Wav.py` places it and stops if it is longer than the loading, see `plans/07_BOOT_NARRATION_PLAN.md`.
The boot loader is followed by a chain for Atari BASIC programs saved in `CSAVE` format with short inter-recording gaps (IRG).
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

A chapter program loads and runs the next load section with `X=USR(2042)`.
While it loads, the intro shows `LOADING` below the cassette, or the text the program passes, for example `T$="LOADING CHAPTER 2":X=USR(2042,ADR(T$),LEN(T$))`.
The text can contain uppercase letters, digits, spaces and `.-:`, up to 38 characters.
This loader and the syncer `X=USR(2045)`, which waits for the next cue of a run section, are in the `loader` folder, see `plans/05_LOADER_MODULE_PLAN.md`.


## Build Tools
The build is started with `Makefile.bat` and requires the following tools.

| Tool | Version | Download | Purpose |
|------|---------|----------|---------|
| Python | 3.9 or later | [python.org](https://www.python.org/downloads/) | Runs `Pack.py`, which compresses the intro with `Zx0.py`, and `Bin2Wav.py`, which builds the tape. Only the standard library is used. |
| MADS | latest | [WUDSN IDE Tools](https://github.com/wudsn/wudsn-ide-tools) | Assembles `boot/Boot.asm` to the plain image `boot/Boot.bin`, from which `Pack.py` writes the boot file `boot/Boot.sec`. |
| Java | 21, latest update | [Adoptium](https://adoptium.net/) | Runs TURGEN. |
| TURGEN | latest | [TURGEN](https://turgen.sourceforge.io/) | Its GENCAS tool converts the boot file and the BASIC programs to 600 baud tape records. |
| AltirraBridge | nightly | [AltirraSDL releases](https://github.com/ilmenit/AltirraSDL/releases/tag/nightly-bridge) | Headless Altirra that boots the new tape and checks the boot file. |
| Altirra | 4.40 | [Altirra](https://www.virtualdub.org/altirra.html) | Plays the tape after the build and is used to edit the BASIC programs. |
| A8CAS | 1.3.1 | [A8CAS](https://a8cas.sourceforge.net/) | Converts cassette recordings to `.cas` tape images, used by the scripts in the `test` folder. |
| Microsoft David | Windows | Windows' English (United States) text-to-speech feature | The voice `Speak.py` speaks the narration with. |

Python is installed globally, for example with the installer from python.org or with `winget install Python.Python.3.13`.
All other tools are downloaded by `Make-Setup.bat` into the `build` folder, which is not part of the repository.
Run it once before the first build. Tools that are already there are kept, so delete a tool's folder in `build` to get its latest version.
It also checks for the narration's voice and, if it is missing, installs the English (United States) text-to-speech feature of Windows, which a Windows in another language lacks; Windows asks for administrator rights for that.
`Make-Settings.bat` adds the folders in `build` to the `PATH`. `Makefile.bat` and `Altirra.bat` call it first.

The downloaded Altirra starts with its built-in AltirraOS and Altirra BASIC.
To use the original Atari OS and Atari BASIC, register your own ROM images in Altirra under System, Firmware.

## Editing
The Atari BASIC files can be editing in Altirra by starting the "Altirra.bat" script followed by `LOAD "H:C1.BAS"`to load the program.

## Tests
The `test-chapters` folder contains an end-to-end test of the sync co-track, started with `test-chapters/TestChapters.bat`.
It builds a tape with the boot code, a test program in `C1.BAS` and a run section with three cues from `C1A.TXT`, and plays it in the headless AltirraBridge emulator at real tape speed.
The test passes if the program reports exactly three cues with the spacing of the cue file, using `basic_syncer` from the boot code.
`C1.WAV` plays while the test program loads, and `C1A.WAV` is the audio of the run section.
In it, the label text of every cue is spoken before the cue and ends shortly before its pulse, so the screen changes when the text has been spoken.
Both contain synthesized speech and are part of the repository. They are written again with `TestChapters.py --write-audio`, for example after changing the cues.
The test keeps its tape as `TestChapters.wav`. `test-chapters/PlayChapters.bat` plays it in the Altirra window at real tape speed, so the test can also be followed and heard interactively. If the tape does not exist yet, it runs the test first.

## Project Members

- Prof. Dr. Stefan Höltgen
- Dr. Torsten Roeder
- Stefan Meyer
- Andreas Kahlenbach
- Peter Dell


