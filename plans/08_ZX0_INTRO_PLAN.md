# Plan: Load the intro ZX0-compressed

Written 2026-11-14. Requested after plan 07: loading the intro and its
animation takes long; analyze what ZX0 compression of the intro would mean
and achieve. Reference: the 6502 decompressor at
<https://xxl.atari.pl/zx0-decompressor/>; compressor: ZX0 by Einar Saukas
(<https://github.com/einar-saukas/ZX0>, BSD-3).

**Status: done 2026-11-14.**

## Current state

| Records | Memory | Content | Loaded by |
|---|---|---|---|
| 1 | $0600-$067F | header, pre-loader | OS |
| 2-3 | $0680-$077F | `motor`, `wait`, `put_char`, `title`, `pause` | pre-loader, then the pause for the title |
| 4 | $0780-$07FF | `show_intro`, `finish`, `booter`, `reset`, jump table | pre-loader |
| 5-23 | $0800-$117F | intro display part: font, display list, screen map, display code | pre-loader, then `show_intro` |
| 24-35 | $1180-$176F | reel frames, animation code, loader module | pre-loader, then `finish` |

A record takes about 2.6 s on the tape (2.2 s for 132 bytes at 600 baud
plus the 0.25 s gap). After the title, 32 records follow: about 83 s, of
which about 50 s pass before the intro shows.

## Measured compression

Sizes from a Python port of ZX0's optimizer (format v2, the default of
ZX0 2.x and the format of the reference's `dzx0_standard`), applied to the
assembled `boot/Boot.sec`:

| Part | Memory | Bytes | ZX0 | Ratio |
|---|---|---|---|---|
| Font | $0800-$0BFF | 1024 | 341 | 33% |
| Screen map | $0C20-$0FDF | 960 | 172 | 18% |
| Display code and variables | $0FE0-$111C | 317 | 268 | 85% |
| Reel frames | $111D-$151C | 1024 | 447 | 44% |
| Animation code, loader module | $151D-$176F | 595 | 482 | 81% |
| **Display part** | $0800-$111C | 2333 | 787 | 34% |
| **Animation part** (frames, code, loader) | $111D-$176F | 1619 | 924 | 57% |
| **Intro and loader, one stream** | $0800-$176F | 3952 | **1614** | 41% |

The graphics and the mostly empty screen map compress well; code hardly
does.

## The decompressor

The reference's format v2 decompressor (`dzx0_standard`) is about 211
bytes, counted from its listing, plus 12 bytes for a `GET_BYTE` that reads
from memory: 223 bytes. It uses 4 zero page bytes and self-modified
operands. The page states no license and no speed.

**Own decompressor (prototype, 2026-11-14): 172 bytes**, plus the same 12
bytes for reading from memory: 184 bytes, 39 bytes less than the
reference. It uses 9 zero page bytes (destination, copy source, length,
negated offset, bit buffer), no self-modified code and no tables, and
needs from `get_byte` only that it keeps the carry. Structure:

- The offset is kept negated, so the copy source is `dst+offs`. The
  inverted Elias code of the offset's MSB, started at $FE, gives `-MSB-1`
  directly; one `inc` gives `-MSB` (0 = end marker), and two `ror`s
  through the carry build the 16-bit negated offset from it and the LSB,
  leaving bit 0 of the LSB in the carry as the first bit of the length.
- One `put` routine stores a byte, advances the destination and counts
  the length down, shared by literals and copies; byte by byte instead of
  page-wise loops, which costs speed, not correctness.

Tested in AltirraBridge against the Python compressor with 7 streams (1
byte, 1000 zero bytes, 1000 random bytes, mixed data, and the intro's
display part, animation part and the whole intro): all decompress
correctly. **Speed: the whole intro (3952 bytes) in 17 frames, 0.34 s**,
about 150 cycles per byte with the screen on: about 27 ms per record of
compressed input, a ninth of the 0.25 s gap.

**Compressor**: a Python port of ZX0's `optimize.c` and `compress.c`
(BSD-3), with a Python decompressor for the round trip, produces the
sizes measured above.

## Proposal: decompress while loading

1. **Streaming `GET_BYTE`.** Instead of loading the compressed data into a
   buffer and decompressing it at the end, `GET_BYTE` takes the next byte
   from the cassette buffer (`CASBUF_DATA`) and calls `RBLOKV` when the
   128 bytes of a record are used up. The intro is then decompressed
   record by record while the tape runs, directly to its final addresses.
   No buffer is needed, and the intro still shows as early as possible.
2. **Showing the intro.** At every record, `GET_BYTE` checks whether the
   output pointer has passed `intro.display_end` and then calls
   `show_intro` once, as the pre-loader does today with `SHOW_ADDRESS`.
3. **End.** The stream's end marker ends the decompression; then `finish`
   reads the end-of-file record as today. `TOTAL_RECORDS` and the
   pre-loader's end check go.
4. **Where the decompressor lives.** It must be loaded uncompressed
   before the stream, but below $0800 only about 140 bytes are free. It is
   needed only during the boot, so it is assembled behind `image_end`
   (above `MEMLO`, BASIC may overwrite it later, no memory cost). The
   pre-loader copies the raw records as today and continues the
   destination at the decompressor's address when it reaches $0800, then
   jumps to it.
5. **Build.** MADS assembles the plain image as today; a new step
   (`Pack.py`) cuts it at the labels from the `.lab` file into the raw part
   (boot record, second stage, decompressor) and the compressed part
   ($0800-`image_end`), and writes `Boot.sec`. It also decompresses the
   stream again in Python and compares it with the image.
6. **Timing.** Between two records, the decompressor produces about 310
   bytes; measured with the prototype, that takes about 27 ms, far below
   the 0.25 s gap before the next record's sync bytes. `Bin2Wav.py` could
   extend single gaps if a real recorder needed more.

## Expected result

| | Today | With ZX0 |
|---|---|---|
| Records after the title | 32 | about 16: 1 raw rest of the second stage, 2 decompressor (184 bytes and the streaming reader), 13 compressed |
| Loading after the title | about 83 s | **about 42 s** |
| Title to intro shown | about 50 s | **about 26 s** (display part 787 bytes, 7 records) |
| Tape length (boot section) | 109.5 s | about 68 s |
| Boot records, pause, title | 1, after record 3 | unchanged |
| BASIC memory (`MEMLO`) | $1770 | unchanged |

The time before the title (records 1-3, about 23 s with the leader) does
not change.

## What it means

- **Narration.** The 66.3 s narration of plan 07 no longer fits: about
  40 s are left after the title. `Bin2Wav.py` stops the build and says by
  how much to shorten it; `boot/Narration.txt` has to lose about a third.
- **Compressor in the build.** Options: (a) `zx0.exe` from the ZX0
  repository, downloaded by `Make-Setup.bat` into `build/`; (b) the Python
  port (about 200 lines with the decompressor, BSD-3 notice kept), which
  keeps the build at "Python standard library only". It takes about 10 s
  for the 4 KB stream.
- **Debugging.** Altirra's debugger and the `.lab` file still show the
  decompressed intro at its addresses; only the tape holds packed data.
- **Tests.** `TestChapters.py` covers the result end to end (title, intro
  with `LOADING`, colors, cues). `Bin2Wav.py`'s boot test compares the
  boot record only and stays valid.
- **Chapters.** The BASIC chapters are loaded by `CLOAD` and stay
  uncompressed; this plan only covers the boot file.

## Costs and risks

- **Decompressor source and license.** Solved by the own decompressor.
- **Timing between records** (point 6), with the display DMA and the VBI
  running. Mitigation: measure in Altirra, extend gaps where needed.
- **Code size in the boot record.** The pre-loader gets the jump to the
  decompressor and loses the show and end checks; it stays within 1
  record (21 bytes are free today).
- **Build time** with a Python compressor.

## Further savings (not part of this plan)

- The code parts compress to 81-85%. Moving more code into fewer bytes
  helps less than the graphics did.
- The reel frames (447 bytes packed) could be generated at run time from
  one frame by code, at the cost of complexity.
- Plain run-length coding of the screen map alone would need no
  decompressor download but saves far less than ZX0 on the whole stream.

## Decisions

Made 2026-11-14:

- The reference decompressor would be acceptable, but a shorter own one is
  preferred: the own decompressor (172 + 12 bytes) is used.
- The Python port is the compressor in the build.
- The decompressor is a file of its own, `zx0/Zx0.asm`.

## Result

- **Files**: `Zx0.py` (compressor, a port of ZX0 with its BSD-3 license
  text, and a decompressor for the round trip), `Pack.py` (writes
  `boot/Boot.sec` from the plain image `boot/Boot.bin` and the labels),
  `zx0/Zx0.asm` (the decompressor, `.proc zx0`, 172 bytes). In
  `boot/Boot.asm`: the pre-loader continues at `unpack_start` when the
  second stage is loaded and jumps to `unpack` when the decompressor is
  loaded; `unpack` (behind `image_end`) streams the records into the
  decompressor, shows the intro once `zx0.dst` has passed
  `intro.display_end`, and returns to the OS through `finish`, or with
  BOOT ERROR from the stack depth saved at its start. `SHOW_ADDRESS` and
  `TOTAL_RECORDS` are gone. `ZP_ZX0` ($80, 9 bytes) is BASIC's zero page,
  free during the boot.
- **Boot file**: 19 records instead of 35: 1 boot record (114 bytes), 3
  second stage, 2 decompressor and streaming reader (245 bytes), 13
  compressed (3952 -> 1614 bytes). `MEMLO` is unchanged ($1770).
- **Times on the tape** (Altirra, real tape speed):

  | | Before | Now |
  |---|---|---|
  | Title typed | 25.6 s | 25.6 s |
  | Intro shown | about 76 s (record 23, estimated) | 54.8 s |
  | BASIC ready, animation starts | 108.8 s | **69.4 s** |
  | Boot section of the tape | 109.5 s | **70.5 s** |

- **Narration**: shortened to 42.7 s (four paragraphs, the sentence on the
  1980s dropped); 4.7 s are left in the boot section.
- `Pack.py` takes about 5 s. `TestChapters.py` packs the boot file the same
  way; it passes, and so does the boot test of the real tape build.
