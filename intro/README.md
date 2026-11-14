# THE ATARI TAPE BOOK – intro

Animated cassette for the Atari 8-bit, ANTIC mode 2 (GRAPHICS 0), using a
single 1 KB character set (78 of 128 chars used). Black screen and border.
It is shown while the tape loads, see `plans/01_INTRO_DURING_LOADING_PLAN.md`.

* Cassette 21x14 chars, centred (col 10, row 5), "ATARI TAPE BOOK" on the label.
* Label letters are in `Intro.fnt` as in the ROM; `intro.start` also copies
  them from the OS ROM charset ($E000), so they are the standard Atari font
  (OS ROM must be enabled at that moment).
* Both reels share the same 16 animated chars (4x4 block). 6 notches → 60°
  period → 8 frames loop seamlessly.
* An immediate VBI animates the reels, so the animation also runs during tape
  I/O. To keep the VBI short, it copies each 128-byte frame in two chunks into
  a second set of reel characters (codes 78-93) and then switches the reel
  positions in the screen map to that set. `SPEED` (even) sets the VBIs per
  step, `DIR = -1` reverses (rewind). Settings at the top of `Intro.asm`.
* Own display list and screen memory (the screen map), so BASIC's output during
  loading does not show. The VBI keeps the display list, font and colours in
  place, and `intro.off` restores those of the OS.
* Colours: `COLOR1=$00` (ink), `COLOR2=$0E` (white, only inside the cassette),
  `COLOR4=$00` (border).

## Files

| File             | Content                                               |
|------------------|-------------------------------------------------------|
| `Intro.asm`      | the intro, included by `boot/Boot.asm` and `Intro-Demo.asm`; entry points `intro.show`, `intro.start`, `intro.on`, `intro.off` |
| `Intro-Data.asm` | 40x24 screen map, reel frames, ROM letter table, constants (included by `Intro.asm`) |
| `Intro.fnt`      | 1 KB font (frame 0, letters as in the ROM)            |
| `Intro-Demo.asm` | standalone demo                                       |
| `Intro-Demo.bat` | builds the standalone demo and starts it in Altirra   |
| `Intro.xex`      | runnable standalone demo                              |
| `gen.py`         | generator for the data, font and preview              |
| `preview.gif`    | preview of the animation                              |

## Build (MADS)

```
python3 gen.py          # only needed after changing the graphics; needs numpy and Pillow
mads Intro-Demo.asm -o:Intro.xex
```

MADS is in the `build` folder after `Make-Setup.bat`, and `Make-Settings.bat` adds it to the `PATH`.
The tape build assembles the intro as part of `boot/Boot.asm`.
