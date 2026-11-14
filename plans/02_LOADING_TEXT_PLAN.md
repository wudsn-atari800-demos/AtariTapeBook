# Plan: "Loading" text with the name of the next section

Written 2026-11-14. Requested after plan 01, to use more of the OS font in
the intro and to show which section is loading.

**Status: planned.**

## Goal

While the intro is on screen, a text line below the cassette shows what is
loading, for example `LOADING CHAPTER 2`. The text uses the standard
characters of the OS font, in the intro's own font.

## Decided

- **Character set: uppercase letters, digits, space and `.-:`.** That is 40
  characters. Lowercase letters do not fit, see "Character layout".
- **Standard character positions.** These 40 characters sit at their
  internal codes of the OS font. A text needs no lookup table: the internal
  code is the ATASCII value minus 32, plus 128 for inverse.
- **No display list interrupt.** Switching to the ROM font for the text
  lines with a DLI does not work while the tape loads, because of the timing
  with which ANTIC asserts the NMI. The text therefore uses the intro's font.
- **Inverse text.** Around the cassette the screen shows the solid
  character in ink (black). Inverse characters show the glyph in the paper
  colour (white) on ink, so the text is white on black like the surrounding.
- **Text source.** The text while the first chapter loads is just
  `LOADING`, a constant in the boot code. Every later text is passed
  complete by the chapter program with the USR call that loads the next
  section, as address and length, for example
  `T$="LOADING CHAPTER 2":X=USR(1550,ADR(T$),LEN(T$))`. A call without a
  text, `X=USR(1550)`, shows `LOADING`, so existing chapter programs keep
  working.

## Character layout

| Characters | Codes |
|---|---|
| Space (also the cassette's blank character) | 0 |
| `-` and `.` | 13, 14 |
| Digits 0-9 | 16-25 |
| `:` | 26 |
| A-Z (also the label letters) | 33-58 |
| Reel character set A | 64-79 |
| Reel character set B | 80-95 |
| Other cassette graphics (52 today) | 1-12, 15, 27-32, 59-63, 96-127 (56 codes) |
| Spare | 4 codes |

Today `gen.py` numbers the cassette characters 0-77 consecutively, which
covers all 40 standard positions. With the layout above, the cassette's
blank character 0 is the space, and the 9 label letters (A B E I K O P R T)
are the standard letters, so they need no codes of their own. The two reel
sets must each be 16 consecutive codes, because the VBI computes a reel
character as base plus offset.

## Target state

1. **`gen.py` assigns the new layout.** The reel sets get fixed bases (64
   and 80), the label letters their standard codes, and every other new
   glyph the next free code from the list above. It fails if the graphics
   need more than the free codes. `Intro-Data.asm` gets a constant for the
   base of reel set B, which `Intro.asm` uses instead of `CAS_NCHARS`.
2. **The standard characters come from the ROM font.** `Intro.fnt` holds the
   9 label letters as today, so the cassette is correct as soon as it is
   shown. `intro.show` copies the 40 standard characters from the ROM font
   ($E000) in three ranges (13-14, 16-26, 33-58), so the text can use them
   from the start. This replaces the label letter copy in `intro.start`.
3. **Text output.** A routine writes a text into row 20 of the screen,
   centred on the 40 columns and inverse, converting ATASCII to internal
   codes. The cassette fills rows 5-18; row 19 stays blank as a gap of one
   character height, rows 21-23 stay blank too.
   `intro.show` and `intro.on` write the line once when the intro switches
   on for the next file; the VBI is not involved, so its timing does not
   change.
4. **Build check.** The build fails if a cassette character lands on a
   standard position, or a text contains a character outside the 40.

## Passing the text

`CLOAD` does not know the name of a program before it is loaded, so the
text comes from the chapter program:

- `basic_loader` (USR 1550) reads the number of arguments that BASIC pushes
  before the arguments. With two arguments, they are the address and the
  length of the text (`ADR` and `LEN` of a BASIC string); with none, the
  text is `LOADING`. Any other number of arguments is treated like none, so
  the stack is always cleaned up correctly.
- Atari BASIC strings have no terminator, and `ADR` passes only the
  address, so the length is passed explicitly.
- Texts longer than the row (38 characters) are cut. Characters outside
  the 40 are shown as spaces; only texts in the boot code can be checked
  by the build.
- `basic_loader` copies the text before it installs the E: hook, so the
  string's memory may change afterwards.

Run sections are not loaded with `CLOAD` and get no text.

## Impact

- **`intro/gen.py`**: the new character layout, the reel set B constant,
  the check against the free codes. Running it needs numpy and Pillow,
  which are installed on the development machine; today's `gen.py`
  reproduces the committed `Intro.fnt` and `Intro-Data.asm` exactly.
- **`intro/Intro.fnt`, `intro/Intro-Data.asm`**: regenerated.
- **`intro/Intro.asm`**: reel set B from the new constant, the ROM copy in
  `intro.show`, the text output routine. The code needed by `intro.show`
  must stay below the font at $0800 (about 140 bytes are free there).
- **`boot/Boot.asm`**: the constant `LOADING`; `basic_loader` takes the
  optional address and length and copies the text.
- **Chapter programs**: pass the text for the next section with the USR
  call; `chapters/C1.BAS` and `test-chapters` get an example.
- **Tests**: `test-chapters` checks the text while `C1.BAS` loads.

## Costs

| Item | Value |
|---|---|
| Font codes | 40 standard characters; 4 codes remain spare |
| Code below $0800 | ROM copy and text output, a few dozen bytes |
| VBI | unchanged |

## Open

Nothing.
