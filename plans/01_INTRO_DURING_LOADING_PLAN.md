# Plan: Show the animated cassette intro while the tape loads

Written 2026-11-14. Requested after the intro (`intro/`) was added and ported
from ca65 to MADS.

**Status: planned.** Done so far: the MADS port (`intro/Intro.asm`), which
builds a `Intro.xex` byte-identical to the former ca65/ld65 build. Nothing
of the integration below is implemented yet.

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

1. **Two-stage boot file on one tape file.** GENCAS writes one file: the
   2 pre-loader records, followed directly by the intro's records, without
   an EOF record in between. The header's record count announces only the
   pre-loader records.
2. **Pre-loader at load address + 6.** Because of step 4 above, the first
   intro record is already at $0400 when the routine starts. It copies that
   record, reads the remaining intro records with `RBLOKV` and copies each
   one, and returns with carry set if a read fails. The motor must keep
   running until the last intro record is read. With short gaps there are
   only about 0.25 s between records, so the work between two reads stays
   short (copying 128 bytes or setting up the display is far below that).
3. **Progressive display.** The intro's records are ordered font, screen
   map, code, reel frames. As soon as the font and the screen map are in,
   the pre-loader switches on the intro's display, so the static cassette
   appears before the reel frames have loaded. The animation starts when
   the frames are complete.
4. **Intro in low memory, protected by `MEMLO`.** The intro is assembled
   from $0700, directly above the boot code: code at $0700-$07FF, font at
   $0800 (1 KB aligned), then screen memory and data. `booter` raises
   `MEMLO` above the intro before it starts BASIC, so BASIC's program area
   starts above it. `CLOAD` relocates programs, because saved files store
   their pointers relative to the program start. Fixed addresses work on
   every RAM size, unlike an intro below `RAMTOP`.
5. **`RESET` keeps the protection.** The OS resets `MEMLO` to $0700 on every
   `RESET`. `booter` sets `CASINI` to a small routine that only restores
   `MEMLO`, and keeps `BOOT?` set, so the OS calls it on every `RESET`.
   Today `booter` clears `BOOT?`.
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
   - The VBI copies the next frame into the hidden set in chunks of 64
     bytes, one chunk per VBI.
   - When the hidden set is complete, the VBI switches the 32 reel
     positions in screen memory (two 4x4 blocks) to the other set, which
     takes about 300 cycles.
   - This keeps the current speed of one step every two VBIs and keeps the
     VBI at about 0.6-0.8 ms.
9. **Switching the intro off.** A chapter program calls a new USR entry
   point in the boot code when it starts. It removes the VBI and restores
   BASIC's display list and the ROM font. The intro's memory stays
   reserved, because BASIC's program area cannot move down again.

## Impact

- **`boot/Boot.asm`**: pre-loader at load address + 6, `MEMLO` and `CASINI`
  handling in `booter`, the USR entry point to switch the intro off.
- **`intro/Intro.asm`**: assembled from $0700 as a plain binary instead
  of an executable, own display list, immediate VBI, chunked
  double-buffered reel characters, no endless loop, no copy into `SAVMSC`.
- **`intro/gen.py`**: the second set of reel characters in the font; the
  record order font, screen map, code, frames.
- **`Bin2Wav.py` / `Makefile.bat`**: the boot file and the intro become one
  GENCAS input file, built from both assemblies.
- **Chapter programs**: call the USR entry point to switch the intro off.
- **Tests**: `test-chapters` gets the intro on its tape. A failing record or
  wrong cue timing in the end-to-end test would show a VBI that is too
  long. Altirra's profiler can measure the VBI's real length.

## Costs

| Item | Value |
|---|---|
| Memory taken from BASIC | about 3.2 KB, less with the screen map used in place |
| Additional loading time before the first chapter | about 26 records, roughly one minute at 600 baud with short gaps |
| BASIC memory on a 16 KB Atari | about 13 KB without the intro, about 10 KB with it |

## Open

- Verify step 4 of the boot sequence with the original Atari OS ROM. If the
  original OS does not read the extra record, the pre-loader reads the
  first intro record itself.
- Whether the intro should already be visible while its own records load
  (progressive display, see target state 3) or only from the first chapter
  on.
- Whether the extra loading time of about one minute is acceptable, or the
  intro data should be made smaller first (only 78 of 128 characters are
  used, and the screen map is mostly blank).
