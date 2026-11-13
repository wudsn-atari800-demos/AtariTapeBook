# Analysis of the Sync Co-Track

This document describes how "Conversational German" keeps the screen in step with the speech, and how the same can be done for the Atari Tape Book.

## How the Original Works
While the speech plays on the left channel, the data channel carries a steady space tone at 3995 Hz.
At each cue point it switches to the mark tone at 5327 Hz for about 335 ms.
The cue points are three to eight seconds apart.

All three programs (`GERMAN11.BAS`, `GERMAN12.BAS`, `GERMAN13.BAS`) contain this statement, decoded from the tokenized BASIC:

```
X=PEEK(53775)/32:B=INT(X+0.5)-INT(X)
```

Address 53775 is the `SKSTAT` register of POKEY. Its bit 4 shows the live level of the data line: 0 during the space tone and 1 during a mark pulse.
Atari BASIC has no bitwise `AND`, so the program extracts the bit with the `INT` construct.
The programs also write to 54018 (`PACTL`), which controls the tape motor, so the motor keeps running while the audio plays.

## Creating a Sync Co-Track
1. **Mark the cue points in each audio file.** For example in Audacity: put a label at every point where the screen should change and export the labels as a text file. The audio and the cues form a run section of their own, for example `C1A.WAV` and `C1A.TXT`, which follows the load section `C1.BAS` on the tape.
2. **Generate the co-track in `Bin2Wav.py`.** For a run section it writes a continuous space tone with a 335 ms mark pulse at each label time, after a one-second lead-in for the motor. The tones are phase-continuous sine waves at the same level as the GENCAS data. GENCAS cannot produce this kind of signal, so `Bin2Wav.py` generates it itself.
3. **Wait for the pulses in each chapter program.** Turn the motor on with `POKE 54018,52`. Then poll the bit in a loop and treat each change from 0 to 1 as the next cue. A 335 ms pulse is long enough for a BASIC loop to see it reliably.

Two details matter:
- **Do not use silence as the base signal.** A8CAS treats silence as a logical 1, and Altirra and a real recorder read it as noise or mark. The steady space tone gives a clean 0 between the pulses.
- **Space the cues sensibly.** Cues much closer than about one second would need a faster loop than BASIC.

The boot check in `Bin2Wav.py` could later be extended to verify the cues. Altirra emulates the `SKSTAT` bit from the tape signal, so the check could count the pulses the emulated Atari actually sees.

## Motor Spin-Up
A wait of 0.5 seconds after starting the motor is enough, but the wait itself is not the critical point.
No measured spin-up time for the 410 or 1010 recorders is available, so the timing below is an estimate.

- **No delay on the data line.** The recorder converts the tones into the bit that is read from `SKSTAT`. That bit follows the tape signal immediately.
- **Only the tone frequencies change during spin-up.** While the tape runs slow, both tones come out lower. The space tone still reads as 0. A mark pulse played too slowly can drop toward the space frequency and be missed or read as noise. The risk is a pulse during spin-up, not reading the bit too early.
- **Usual estimate.** Small cassette motors typically reach speed within a few hundred milliseconds.

Recommendations:
- **Leave a gap before the first cue.** Put the first pulse at least one to two seconds after the motor starts for an audio section.
- **Ignore the bit at the start.** Start the motor and skip `SKSTAT` for about half a second, to avoid a false edge while the tape speeds up.
- **Keep the motor running during the audio.** Then it only spins up once per section. Stopping it between cues, for example to wait for a key, means another spin-up at every restart, and the speech sounds slowed at the start of each restart.

The original course is very cautious here. Measured from its `.cas` file, the gaps between the end of the program data and the first sync pulse are:

| Section | Data ends | First pulse | Gap |
|---------|-----------|-------------|-----|
| 1 | about 268 s | about 271.6 s | about 3.5 s |
| 2 | about 727.5 s | about 735.2 s | about 8 s |

These gaps also include finishing the load and starting the program, but they show that the first cue was never placed near a motor start.
