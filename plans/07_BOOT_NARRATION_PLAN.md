# Plan: A narrator speaks while the intro loads

Written 2026-11-14. Requested after plan 06: a narrator voice talks from
the moment the loading continues after the title is typed until the next
chapter starts.

**Status: done 2026-11-14.**

## Decisions

Made 2026-11-14:

- The narration is in English.
- It covers the intro load only: from the motor restart after the title
  until the boot has loaded everything. `chapters/C1.WAV` keeps playing
  while chapter 1 loads.
- I draft the English text.
- Its length must follow the loading time, which will shrink when the
  loaded parts are compressed in a next step.

## Current state

- After the pause (plan 04), the pre-loader reads the intro for about 83 s
  (25.7 s to 108.8 s of the tape), with the data noise silenced (`SOUNDR`
  = 0, set in `title`). The left channel is silent there.
- `Bin2Wav.py` already looks for `<base>.WAV` for every load section,
  including the boot file (`boot/Boot.WAV`), but puts it at the start of
  the section, under the leader, where the motor runs before the title.

## Proposal

1. **Narration text** in `boot/Narration.txt`: plain English text,
   paragraphs separated by blank lines. Not `Boot.TXT`, which would be read
   as cues.
2. **Speech synthesis** with `Speak.py` in the project root: text file in,
   16-bit mono .wav out, with the Windows speech synthesizer and an English
   voice (as `TestChapters.py` already does). `boot/Make-Narration.bat`
   writes `boot/Boot.WAV` from `boot/Narration.txt`. Like the chapters'
   .wav files, it is not committed (`*.wav` in `.gitignore`): `Makefile.bat`
   speaks it if it is missing, and keeps an existing one, so a real
   recording can replace it under the same name.
3. **Placement in `Bin2Wav.py`**: for a two-stage boot file, the boot
   section's audio starts in the extended gap after the pause record,
   `NARRATION_DELAY_S` (1.0 s) after the gap starts, where the motor
   stops before the title. The tape stands still while the title is typed
   and moves on with the audio when the motor restarts. `extend_gaps`
   returns the gap positions for this.
4. **Length check.** The narration must end before the end of the boot
   section. `Bin2Wav.py` prints the time available and stops with an error
   if the narration is longer, so after compressing the intro the text has
   to be shortened (or the build tells by how much). The other load
   sections keep their audio at the section start.
5. **Text length.** About 70 s of speech for today's 83 s, so the
   narration ends before the intro starts animating. When the loading gets
   shorter, the text is cut and the .wav regenerated.

## Impact

- **New**: `Speak.py`, `boot/Narration.txt`, `boot/Make-Narration.bat`.
- **`Makefile.bat`**: speaks `boot/Boot.WAV` if it is missing.
- **`Bin2Wav.py`**: the boot section's audio offset and length check,
  docstring.
- **README**: the narration and how to regenerate it.
- **Unchanged**: the Atari code, the BASIC programs, the tests (the test
  tape's boot file in a temporary folder has no .wav).

## Costs and risks

- **Synthesized voice.** Microsoft Zira or David sound mechanical; the
  placeholder is meant to be replaced by a recording.
- **Motor stop timing.** A real recorder coasts a little after the motor
  stops. Starting the audio 1.0 s into the gap keeps the first words from
  playing before the title.
- **Tape length** does not change: the audio lies under existing records.

## Test

- `Bin2Wav.py` reports the narration's start and the time left.
- `test-chapters/TestChapters.bat` and the boot test of the real tape build
  pass.
- Listen in Altirra (`Makefile.bat`): the voice starts after the title.

## Result

- `boot/Narration.txt`: six short paragraphs about the tape book, spoken
  by Microsoft David (the first en-US voice) in 66.3 s.
- On the tape the narration runs from 23.1 s (1.0 s into the pause gap,
  about 0.8 s after the point where the motor stops in Altirra) to 87.5 s;
  the boot section leaves 20.1 s spare. `NARRATION_DELAY_S` went from the
  proposed 0.5 s to 1.0 s, because the motor stops only about 0.3 s before
  0.5 s into the gap.
- `boot/Boot.WAV` is not committed, as `*.wav` is ignored like the
  chapters' audio; `Makefile.bat` speaks it when it is missing.
- `Bin2Wav.py` stops with the time available and by how much to shorten
  if the narration does not fit.
- `test-chapters/TestChapters.bat` passes, and so does the boot test of the
  real tape build.
