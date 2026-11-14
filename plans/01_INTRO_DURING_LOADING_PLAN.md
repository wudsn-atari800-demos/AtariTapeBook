# Plan: Show the animated cassette intro while the tape loads

Written 2026-11-14. Requested after the intro (`intro/`) was added and ported
from ca65 to MADS.

**Status: executed 2026-11-14.** Before the plan, the intro was ported to
MADS (`intro/Intro.asm`, byte-identical to the former ca65/ld65 build) and
its files renamed from `cassette` to `Intro`. The target state below is
updated to the executed state. Deviations from the plan as first written:

- **Switching on and off is automatic.** The boot code's E: hook, which
  types `CLOAD` and `RUN`, switches the intro on before `CLOAD` and off
  when it starts typing `RUN`, because `CLOAD` is complete then. So the
  intro shows while every chapter loads, and chapter programs need no USR
  call (target state 9).
- **The extra record read works either way.** The pre-loader compares the
  cassette buffer with the last boot record. If they are equal, the OS did
  not read the extra record, and the pre-loader reads it itself. The
  original Atari OS is still untested, see "Open".
- **The code is split around the font.** Only the pre-loader is in the
  record the OS loads (`BOOT_RECORDS` = 1). The intro's display code and
  variables follow below the font at $0800; the animation code, the label
  letter copy, and the boot code that runs only after everything is loaded
  (`booter`, the E: hook, the BASIC syncer) come after the reel frames.
- **`gen.py` is unchanged.** The second set of reel characters is filled by
  the VBI at run time, and `Intro.fnt` already holds the label letters, so
  copying them from the ROM font moved from `show` to `start`.
- **The VBI is longer than estimated** but stays below one bit: measured
  1,670-1,750 cycles including the OS's part, see "Costs".

## Current state

- **Boot file.** `boot/Boot.asm` assembles to a 191-byte boot file at $0600,
  loaded as 2 records. Its routine at load address + 6 stops the motor and
  returns with `CLC`. The init routine `booter` clears `BOOT?` and `COLDST`,
  installs the E: hook that types `CLOAD` and `RUN`, and starts BASIC.
- **Intro.** `intro/Intro.asm` is a standalone executable at $2000-$2C95:
  a 1 KB font at $2000, code from $2400, then the 960-byte screen map, the
  ROM letter tables, 8 reel frames of 128 bytes each and two variables. It
  copies the screen map into BASIC's text screen (`SAVMSC`), sets `CHBAS` to
  its font, animates the reels from a deferred VBI and then loops forever.
- **Why it cannot run during loading as it is:**
  1. It never returns, so the boot could not continue to `CLOAD`.
  2. $2000 lies inside BASIC's program area: chapters of 12 KB, like the
     "Conversational German" programs, reach past $3700.
  3. It draws into BASIC's text screen and replaces BASIC's font, so
     `CLOAD`, `Ready` and the chapter output would garble the picture, and
     BASIC's text would appear in the intro font.
  4. The OS skips deferred VBIs while serial I/O runs, which is exactly when
     the tape loads, so the animation would freeze.

## How the OS boots from cassette

Verified in the AltirraOS kernel source (`Kernel/source/Shared/boot.s`,
`BootCassette`); still to be verified with the original Atari OS ROM.

1. Open the cassette in continuous mode (`FTYPE=$80`, motor keeps running).
2. Read the first record; take the flags, the number of records, the load
   address and the init address (stored in `CASINI`) from its first 6 bytes.
3. Read and copy the remaining records.
4. Read one more record, normally the EOF record. Its outcome is ignored.
5. Jump to load address + 6. Carry set: close the cassette and show
   `BOOT ERROR`. Carry clear: call `CASINI`, set `BOOT?`=2, jump through
   `DOSVEC`.

At step 5 the cassette is still open and the motor still runs, so the
routine at load address + 6 can read more records itself with `RBLOKV`
($E47A); each record's 128 data bytes arrive at $0400.

## Target state

1. **Two-stage boot file on one tape file.** `boot/Boot.asm` includes the
   intro and assembles both into one `Boot.sec`, which GENCAS writes as one
   file. The header's record count announces only the pre-loader's record.
2. **Pre-loader at load address + 6.** The routine at load address + 6
   jumps to the pre-loader; the BASIC entry points stay at 1550 and 1554.
   Because of step 4 above, the first intro record is normally already at
   $0400; the pre-loader compares the buffer with the last boot record and
   reads the record itself if the OS did not. It copies each record, reads
   the next one with `RBLOKV` and returns with carry set if a read fails.
   After the last intro record it reads the EOF record, so `CLOAD` starts
   at the next file, then stops the motor.
3. **Progressive display.** The image is ordered display code, font, display
   list, screen map and letter table, reel frames, animation code. As soon
   as everything up to the reel frames is loaded, the pre-loader calls
   `intro.show`, so the static cassette appears while the last 8 records
   load. When all records are in, it calls `intro.start`.
4. **Intro in low memory, protected by `MEMLO`.** Memory layout:

   | Part | Addresses |
   |---|---|
   | Boot record: header, BASIC entry points, pre-loader | $0600-$067D |
   | Intro display code and variables | $067E-$0775 |
   | Font (1 KB aligned) | $0800-$0BFF |
   | Display list, screen map, letter table | $0C00-$1003 |
   | Reel frames, animation code, frame table | $1004-$14FF |
   | `booter`, E: hook, BASIC syncer | $1500-$15CA |

   `booter` sets `MEMLO` to $15CB before it starts BASIC, so BASIC's program
   area starts above everything. `CLOAD` relocates programs, because saved
   files store their pointers relative to the program start. Fixed
   addresses work on every RAM size, unlike an intro below `RAMTOP`.
5. **`RESET` keeps the protection.** The OS resets `MEMLO` to $0700 on every
   `RESET`. `booter` sets `CASINI` to a small routine that only restores
   `MEMLO`, and sets `BOOT?` to 2 instead of clearing it, so the OS calls
   that routine on every `RESET`.
6. **Own display list and screen memory.** The screen map is the intro's
   screen memory, so the 960-byte copy into `SAVMSC` is no longer needed.
   BASIC's start reopens the screen and resets `CHBAS`, so the VBI restores
   the intro's display list (`SDLSTL`) and font (`CHBAS`) every frame while
   the intro is active.
7. **Immediate VBI.** The animation runs from the immediate VBI (`SETVBV`
   with A=6), which also runs during serial I/O.
8. **Short VBI through double-buffered reel characters.** The OS measures
   the tape speed before every record by polling `SKSTAT` for the 19 edges
   of the two $55 sync bytes, with interrupts enabled. A VBI longer than
   one bit (1.67 ms, about 2,950 cycles at 600 baud) can make the loop miss
   a pair of edges, which makes the measured speed about 10% wrong and the
   record fail. Copying all 128 bytes of a frame takes about 1,920 cycles,
   about 2,400-2,700 with the OS's own immediate VBI, which is too close.
   Instead:
   - The font holds a second set of the 16 reel characters in its unused
     slots (78 of 128 characters are used), so no second 1 KB font is
     needed.
   - The VBI copies the next frame into the hidden set in two chunks, 48
     bytes in the first VBI of a step and 80 bytes in the second.
   - In the first VBI of a step, before its chunk, it switches the 32 reel
     positions in screen memory (two 4x4 blocks) to the set completed last.
   - This keeps the speed of one step every two VBIs (`SPEED` = 2).
9. **Switching the intro on and off.** The E: hook in the boot code calls
   `intro.on` before it types `CLOAD` and `intro.off` when it starts typing
   `RUN`. `intro.off` removes the VBI and restores the display list, font
   and colours that the VBI saved from the OS. The intro's memory stays
   reserved, because BASIC's program area cannot move down again.

## Impact

- **`boot/Boot.asm`**: pre-loader, `MEMLO` and `CASINI` handling in
  `booter`, intro on and off in the E: hook, the late code moved behind the
  intro.
- **`intro/Intro.asm`**: an include file with local labels (`intro.show`,
  `intro.start`, `intro.on`, `intro.off`), own display list, immediate VBI,
  chunked double-buffered reel characters, no endless loop, no copy into
  `SAVMSC`. The new `intro/Intro-Demo.asm` builds the standalone
  `Intro.xex`.
- **`Bin2Wav.py`**: the boot check stops at load address + 6 and compares
  only the announced boot records, because the intro changes itself after
  loading. `Makefile.bat` is unchanged.
- **Chapter programs**: unchanged.
- **Tests**: `test-chapters` runs with the intro on its tape and also checks
  that the intro is on screen while `C1.BAS` loads and off when it runs.

## Verification

- `TestChapters.bat` passes with the intro: all intro records load, `CLOAD`
  finds `C1.BAS`, the cue spacing is unchanged.
- Probes with AltirraBridge on the test tape and the real tape: the intro
  appears while its last records load, animates while chapter 1 and
  chapter 2 load, and is off while they run. `MEMLO` is $15CB after the
  boot and after `RESET`.
- The standalone `Intro.xex` runs and animates.

## Costs

| Item | Value |
|---|---|
| Memory taken from BASIC | 3.7 KB (`MEMLO` $15CB instead of $0700) |
| Additional loading time before the first chapter | 31 records, 73 s at 600 baud with short gaps (boot section 100 s instead of 27 s) |
| BASIC memory on a 16 KB Atari | about 13.3 KB without the intro, about 9.6 KB with it |
| VBI length while a chapter loads, including the OS's part | 1,670-1,750 cycles, measured over 200 VBIs; one bit at 600 baud is about 2,950 cycles |

The VBI can no longer make the OS miss a pair of edges in its speed
measurement. If a VBI falls on the first or last measured edge, the
measured speed can still be up to about 3% off; all loads in the emulator
succeeded.

## Open

- Verify the boot with the original Atari OS ROM. The pre-loader handles
  both variants of step 4, but only AltirraOS was tested.
- Verify on real hardware, in particular the speed measurement with the VBI
  running (see "Costs").
- Whether the extra loading time of 73 s is acceptable, or the intro data
  should be made smaller (only 78 of 128 characters are used, and the
  screen map is mostly blank).
- About 140 bytes between the display code and the font at $0800 are
  unused; the late boot code (203 bytes) does not fit there.
