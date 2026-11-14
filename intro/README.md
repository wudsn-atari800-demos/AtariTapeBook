# THE ATARI TAPE BOOK – intro

Animated cassette for the Atari 8-bit, ANTIC mode 2 (GRAPHICS 0), using a
single 1 KB character set. Black screen and border. It is shown while the tape
loads, with a text such as "LOADING" below the cassette, see
`plans/01_INTRO_DURING_LOADING_PLAN.md` and `plans/02_LOADING_TEXT_PLAN.md`.

* Cassette 21x14 chars, centered (col 10, row 5), "ATARI TAPE BOOK" on the label.
* Character layout: space, `-.:`, the digits and the uppercase letters sit at
  their standard internal codes of the OS font; `intro.show` copies these 40
  characters from the OS ROM charset ($E000), so they are the standard Atari
  font (OS ROM must be enabled at that moment). The label letters are also in
  `Intro.fnt`. The reel character sets sit at codes 64 and 80, the other 51
  cassette characters at the remaining codes; 5 codes are spare.
* Colors: white ink on black paper, so the blank character $00 fills the
  background. The white label and windows are the inverse blank ($80), the
  label letters the inverse standard letters (black on white).
* Text: row 20, one row below the cassette, centered, white on black.
  `intro.set_text` sets it, `intro.show` and `intro.on` write it; the
  initial text is `LOADING`. Characters outside the 40 show as spaces.
* Both reels share the same 16 animated chars (4x4 block). 6 notches → 60°
  period → 8 frames loop seamlessly.
* An immediate VBI animates the reels, so the animation also runs during tape
  I/O. To keep the VBI short, it copies each 128-byte frame in two chunks into
  a second set of reel characters (codes 80-95) and then switches the reel
  positions in the screen map to that set. `SPEED` (even) sets the VBIs per
  step, `DIR = -1` reverses (rewind). Settings at the top of `Intro.asm`.
* Own display list and screen memory (the screen map), so BASIC's output during
  loading does not show. The VBI keeps the display list, font and colors in
  place, and `intro.off` restores those of the OS.
* Color registers: `COLOR1=$0E` (ink, white), `COLOR2=$00` (paper, black),
  `COLOR4=$00` (border).

## Files

| File             | Content                                               |
|------------------|-------------------------------------------------------|
| `Intro.asm`      | the intro, included by `boot/Boot.asm` and `Intro-Demo.asm`; entry points `intro.show`, `intro.start`, `intro.on`, `intro.off`, `intro.set_text` |
| `Intro-Data.asm` | 40x24 screen map, reel frames, constants (included by `Intro.asm`) |
| `Intro.fnt`      | 1 KB font (cassette characters, reel frame 0, label letters as in the ROM) |
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
