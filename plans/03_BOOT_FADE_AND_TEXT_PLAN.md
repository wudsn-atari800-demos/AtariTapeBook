# Plan: Fade out the boot screen and type the title before the intro loads

Written 2026-11-14. Requested after plan 02.

**Status: planned.**

## Goal

When the pre-loader starts, it fades the boot screen to black, then types
`ATARI TAPE BOOK` (inverse) and `LOADING` (normal) letter by letter, with a
delay of 10 frames per letter, and only then continues loading the intro.
The tape motor is stopped during that time.

## Current state

- The OS loads one boot record ($0600-$067D, 2 bytes free) and calls the
  pre-loader at load address + 6. The pre-loader reads the intro's records
  at once; the screen shows the OS boot screen until `intro.show` switches
  to the intro, after about 70 seconds.
- `wait` (wait A frames on `RTCLOK`) is in the late part of the boot code,
  behind the intro, so it is not loaded when the pre-loader starts.
- `intro.on` saves `COLOR1`, `COLOR2` and `COLOR4` when the intro switches
  on and `intro.off` restores them.
- The tape has short gaps (0.25 s) between all records of the boot file.

## Target state

1. **Stop the motor.** The pre-loader stops the motor first
   (`jsr motor.stop`), so the tape does not run on while the screen is
   faded and the texts are typed. `motor` in the boot record controls the
   motor centrally for the whole boot code.
2. **Keep the OS colors.** It saves `COLOR0`-`COLOR4` before the fade. The
   first `intro.on` takes these saved values as the OS colors to restore,
   instead of the faded ones; `intro.on`/`intro.off` save and restore all
   five registers.
3. **Fade.** It decreases the luminance (low nibble) of `COLOR0`-`COLOR4`
   by 2 per step, one step every 2 frames, until all are 0, then sets all
   five to 0 (black). The OS's deferred VBI copies the shadow registers to
   the hardware, because no serial I/O runs at that time. From a
   luminance of 14, this takes 7 steps, about 0.3 s.
4. **Prepare the screen.** It clears the OS screen memory (`SAVMSC`, 960
   bytes) and sets `CRSINH`, so the cursor does not show, and sets the
   intro's colors: `COLOR1` = $0E (ink white), `COLOR2` and `COLOR4` = $00.
5. **Type the texts.** It writes `ATARI TAPE BOOK` as inverse characters
   and then `LOADING` as normal characters directly into the screen memory,
   one letter every 10 frames (`lda #10`, `jsr wait`). The title shows black
   letters in white cells, like the cassette's label it later sits in;
   `LOADING` shows white on black, like the intro's text. The positions are
   those the intro uses: the label row (row 7, columns 13-27) and the text
   row (row 20, centered), so both texts stay in place and look the same
   when the intro's display replaces the OS screen. The OS font has the
   letters at the same codes as the intro's font. 22 letters take 220
   frames, about 4.4 s.
6. **Restart the motor.** It starts the motor (`jsr motor.start`), waits about
   0.5 s for it to reach its speed, and then continues reading the intro's
   records as today.
7. **Longer gaps on the tape.** A stopped and restarted motor needs a
   longer gap before the next record than the 0.25 s of the short gaps.
   `Bin2Wav.py` extends the gap after the boot record and the gap after
   the first intro record to 2 s of mark tone, so the next record starts
   after the motor is at speed, whether or not the OS read the first intro
   record before calling the pre-loader (see plan 01, "How the OS boots
   from cassette").

## Memory

The fade, the screen preparation, the typing, `wait` and the two texts
must be in the records the OS loads, because they run before the
pre-loader reads anything. That is about 140 bytes more than the boot
record holds, so `BOOT_RECORDS` becomes 3 ($0600-$077F).

The intro's display code ($067E-$07C0 today) then no longer fits below the
font at $0800. Two ways:

- **Display code after the screen map.** `gen.py` writes the screen map and
  the reel frames into two files, and `Intro.asm` places the display code
  and its variables between them: font at $0800, display list, screen map,
  display code, reel frames, animation code. The rest of the space below
  $0800 takes the late boot code that fits there. The progressive display
  of plan 01 stays: the cassette appears while the reel frames load.
- **No progressive display.** `intro.show` runs when all intro records are
  loaded, and the display code moves behind the reel frames. Simpler, and
  the typed texts already show that the tape loads; the cassette appears
  about 20 s later than today.

## Impact

- **`boot/Boot.asm`**: fade, screen preparation, typing, motor stop and
  restart with `motor` in the pre-loader; `wait` and the texts in the boot records;
  `BOOT_RECORDS` = 3; the saved OS colors.
- **`intro/Intro.asm`**: save and restore `COLOR0`-`COLOR4`; take the
  pre-loader's saved colors at the first `intro.on`; the new layout,
  depending on the decision in "Memory".
- **`intro/gen.py`**: two output files, if the display code moves after
  the screen map.
- **`Bin2Wav.py`**: the two extended gaps in the boot file's section.
- **Tests**: `test-chapters` checks that both texts appear on the OS screen
  before the intro, and that the OS colors are back when `C1.BAS` runs.

## Costs

| Item | Value |
|---|---|
| Time before the intro continues loading | about 0.3 s fade, 4.4 s typing, 0.5 s motor start |
| Additional tape length | about 3.5 s for the two extended gaps |
| Memory taken from BASIC | about 150 bytes for the fade and typing code, the texts and the saved colors |

## Open

- Memory: display code after the screen map (keeps the progressive
  display), or no progressive display.
- The fade speed (one step every 2 frames) and the motor start delay
  (0.5 s), to be checked on real hardware.
