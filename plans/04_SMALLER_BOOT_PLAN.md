# Plan: Make the boot records smaller

Written 2026-11-14. Requested after plan 03, which grew the records the OS
loads from 2 to 3.

**Status: done 2026-11-14 (option B).**

## Current state

The OS loads 3 records ($0600-$074D, 334 bytes; 2 records hold 256):

| Part | Addresses | Bytes |
|---|---|---|
| Header, `jmp preloader`, padding, BASIC entry points 1550 and 1554 | $0600-$0615 | 22 |
| `motor`, `wait`, `put_char` | $0616-$0631 | 28 |
| `title`: fade, screen setup, `print_text`, texts, saved colors | $0632-$06C6 | 149 |
| `preloader` | $06C7-$074D | 135 |

The pre-loader in detail:

| Part | Bytes | Runs |
|---|---|---|
| Motor stop, `title`, motor start, wait | 16 | before any intro record |
| Check whether the OS read one record more | 16 | before any intro record |
| Copy loop | 29 | after every record |
| Show check (`shown`, `display_end`) | 15 | after every record |
| Show action: `intro.show`, `SOUNDR`, colors to the intro, clear the OS screen | 26 | once, when the display is loaded |
| End check and next read | 16 | after every record |
| `done`: EOF record, `intro.start`, motor stop | 10 | once, at the end |
| `read_record`, `shown` | 7 | from the start |

Only code that runs before the pre-loader has read anything, or after every
record, has to be in the records the OS loads.

## Option A: move only what runs later

1. **BASIC entry points out of the boot records.** The padding and the two
   stubs (13 bytes) and the `jmp preloader` at load address + 6 (3 bytes)
   go: the pre-loader starts directly at load address + 6. The entry points
   become a jump table at a fixed address directly below the intro's font,
   `INTRO_FONT_ADDRESS-6`, which stays stable when code moves: `jmp
   loader_text` at $07FA (USR 2042) and `jmp syncer` at $07FD (USR 2045);
   `syncer` pulls the argument count itself. Saves 16 bytes.
2. **Show action into the late part.** A procedure `show_intro` below $0800
   takes `intro.show`, the silence, passing the colors and clearing the OS
   screen; the pre-loader calls it. Saves 23 bytes.
3. **Show check without a flag.** The pre-loader calls `show_intro` when
   the destination pointer equals the first record boundary at or above
   `intro.display_end`, so `shown` and `inc shown` go. Saves 3 bytes.
4. **`done` into the late part** as `finish`, reached with a jump. Saves
   5-8 bytes.

Together about 50 bytes: 284 bytes, still 3 records. Reaching 2 records
would need about 28 bytes more from the title's features (key click,
random delay) or from the check for the extra record.

## Option B (recommended): load the title as part of the second stage

The title code does not have to be loaded by the OS. The pre-loader can
read it as the first records of the second stage, with the motor running,
and stop the motor only then:

1. **Boot record**: header, `motor`, and the pre-loader (check for the
   extra record, copy loop, show check, pause check, end check,
   `read_record`), about 110 bytes: **1 record**.
2. **Second stage below $0800** ($0680-$07FF, 384 bytes): `wait`,
   `put_char`, `title` with its texts and saved colors, `show_intro`,
   `finish`, `booter`, `reset`, `syncer` and the BASIC jump table, about 270
   bytes.
3. **Pause point.** When the destination pointer reaches the first record
   boundary behind `title`'s code and data (`PAUSE_ADDRESS`), the
   pre-loader stops the motor, calls `title`, restarts the motor, waits
   and reads on. This replaces the prologue at the start.
4. **One extended gap.** The pause happens after a fixed record that the
   pre-loader has read itself, whatever the OS did before calling it. So
   only the gap after that record needs to be extended, not two: the tape
   gets 2 s shorter. `Bin2Wav.py` needs the record number: the boot
   header's first byte, which the OS copies to `DFLAGS` and otherwise
   ignores for cassette boot, carries it (`PAUSE_RECORD`), computed by MADS.
5. **The title starts at about the same time.** Today the OS loads 3
   records and reads 1 more before the title; with option B it loads 1 and
   the pre-loader reads about 3 more, the same 4 records.

Option B also includes points 1, 2 and 4 of option A.

## Impact

- **`boot/Boot.asm`**: the new layout, the pause point, `show_intro` and
  `finish`, the jump table, `PAUSE_RECORD` in the header (option B).
- **`AtariTapeBookEquates.asm`**: `USR_LOADER` = 2042, `USR_SYNCER` = 2045.
- **BASIC programs**: `chapters/C1.BAS` (USR 1550), `chapters/C2.BAS` and
  `test-chapters/C1.BAS` (USR 1554) get the new addresses; they are
  regenerated from their listings, as in plans 02 and 03.
- **`Bin2Wav.py`**: extend one gap, after the record from the header's
  first byte, instead of two (option B).
- **`TestChapters.py`**: the syncer address it checks.
- **Documentation**: the README's chapter description with the USR calls.

## Costs and risks

- **New USR addresses.** Every chapter program must call 2042 and 2045
  instead of 1550 and 1554. The build cannot check BASIC programs, but the
  end-to-end test covers the syncer.
- **Header byte 0** (option B). It must be verified with the original
  Atari OS that a non-zero first header byte does not change the cassette
  boot. If it does, `Bin2Wav.py` gets the record number as an option from
  `Makefile.bat` instead.
- **Memory.** BASIC's free memory does not change: `MEMLO` is set by the
  code behind the intro.

## Open

- Option A or B.
- The address of the jump table: below the font (USR 2042/2045, proposed)
  or another fixed address.

## Result

Option B, with the jump table below the font (USR 2042 and 2045).

| Part | Addresses | Bytes |
|---|---|---|
| Boot record: header, `preloader` with `read_record` | $0600-$066A | 107 |
| Pause code: `motor`, `wait`, `put_char`, `title`, `pause` | $066B-$0729 | 191 |
| `show_intro`, `finish`, `booter`, `reset`, `syncer` | $072A-$0787 | 94 |
| Free | $0788-$07F9 | 114 |
| Jump table `basic_loader`, `basic_syncer` | $07FA-$07FF | 6 |

- The OS loads **1 record** instead of 3. The pre-loader reads records 2
  and 3 (`PAUSE_RECORD` = 3, in header byte 0) and then pauses for the
  title; AltirraOS's extra read is still handled.
- `Bin2Wav.py` reads the pause record from header byte 0 and extends only
  the gap after it; the boot section is 2 s shorter.
- `motor` stays out of the boot record: only the pause uses it.
- Tested with `test-chapters/TestChapters.bat` (PASS: title typed, intro
  with `LOADING`, colors restored, cues in order) and the boot test of the
  real tape build.
- Still open: a run with the original Atari OS to confirm that a non-zero
  header byte 0 does not change the cassette boot (the OS copies it to
  `DFLAGS` and does not use it otherwise).
