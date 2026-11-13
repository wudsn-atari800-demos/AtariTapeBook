# Atari Tape Book

The Atari Tape Books is a software for Atari 8-bit computer with at least 16k of RAM (Atari 400/800/XL/XE).

## Tape Format
The software is provide as a stereo tape in ".wav" format with 44.1kHz sample rate and 16-bit resolution.
The left channel contains the audio-track, the right channel contain the data track with standard 600 baud data rate.
The data track contains a short boot loader, to alloed booting with the "START" pressing during power-up.
The bool loader is followed by a chain for Atari BASIC programs saved in "CSAVE" format with short inter-recording gaps (IRG).
The short IRGs reducde the loading time.

# Folder
The chapters of the book are stored in the "chapters" folder.
For every chapter there is a "C<n>.BAS" file in tokenized Atari BASIC format and a "C<N>.WAV" file wich can be in mono or stereo format.
The build process automatically converts the ".WAV" file to a mono track in the output format of the tape.


# Editing
The Atari BASIC files can be editing in Altirra by starting the "Altirra.bat" script followed by `LOAD "H:C1.BAS"`to load the program.
 