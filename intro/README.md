# THE ATARI TAPE BOOK – intro

Animated cassette for the Atari 8-bit, ANTIC mode 2 (GRAPHICS 0), using a
single 1 KB character set (78 of 128 chars used). Black screen and border.

* Cassette 21x14 chars, centred (col 10, row 5), "ATARI TAPE BOOK" on the label.
* Label letters are copied from the OS ROM charset ($E000) at start-up, so they
  are the standard Atari font (OS ROM must be enabled at that moment).
* Both reels share the same 16 animated chars (4x4 block). 6 notches → 60°
  period → 8 frames loop seamlessly; one step copies 128 bytes into the font.
* A deferred VBI steps the animation every `SPEED` frames; `DIR = -1` reverses
  (rewind). Settings at the top of `cassette.s`.
* Colours: `COLOR1=$00` (ink), `COLOR2=$0E` (white, only inside the cassette),
  `COLOR4=$00` (border).

## Files

| File              | Content                                               |
|-------------------|-------------------------------------------------------|
| `cassette.xex`    | runnable demo                                         |
| `cassette.s`      | demo source (ca65)                                    |
| `cassette.cfg`    | ld65 linker config                                    |
| `cassette_data.s` | 40x24 screen map, reel frames, ROM letter table, constants |
| `cassette.fnt`    | 1 KB font (frame 0, letters as in the ROM)            |
| `gen.py`          | generator for the data, font and preview              |
| `preview.gif`     | preview of the animation                              |

## Build (cc65)

```
python3 gen.py          # needs numpy and Pillow
ca65 cassette.s
ld65 -C cassette.cfg cassette.o -o cassette.xex
```
