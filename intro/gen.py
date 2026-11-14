#!/usr/bin/env python3
"""THE ATARI TAPE BOOK intro - cassette with label text, ANTIC mode 2.

Cassette 21x14 chars (168x112 px), centered on a black 40x24 screen. The reels
are 4x4-char blocks sharing the same 16 animated chars (8 frames, 128 bytes
each). The label letters use the standard Atari font.

Character layout (see plans/02_LOADING_TEXT_PLAN.md): space, "-.:", the digits
and the uppercase letters sit at their standard internal codes of the OS font,
so texts can be written with them; the program copies these 40 characters
from the OS ROM charset at start-up. The reel character sets A and B (16
consecutive codes each) sit at 64 and 80, all other cassette characters take
the remaining codes. The font file holds the label letters (from the table
below) and reel set A; set B is filled at run time.

Colors: white ink (COLOR1) on black paper (COLOR2), so the blank character 0
fills the background. The white parts are set pixels; the white label and
windows use the inverse space ($80), and the label letters are the inverse
standard letters (black on white).
Output: Intro.fnt, Intro-Data.asm (constants, screen map), Intro-Frames.asm (reel frames), preview.gif
"""
import math
import os
import numpy as np
from PIL import Image

COLS, ROWS = 21, 14
W, H = COLS * 8, ROWS * 8
SS = 8
NFRAMES = 8                       # frames per 60 deg (6 notches)
REEL_ROW = 4                      # reel blocks: rows 4..7
REEL_COLS = (4, 13)               # cols 4..7 and 13..16 -> centers x=48, x=120
RB = 4                            # reel block size in chars
RC = [(c * 8 + RB * 4, REEL_ROW * 8 + RB * 4) for c in REEL_COLS]
REEL_R = 13.0
PILL_R = 23.0
TEXT = "ATARI TAPE BOOK"
TEXT_ROW, TEXT_COL = 2, 3         # label text position inside the cassette
CAS_X, CAS_Y = 10, 5              # cassette position on the 40x24 screen

# Standard Atari OS font (used for the preview only - the program copies the
# real glyphs from the ROM charset at $E000 at start-up).
ATARI_ROM = {
    'A': [0x00, 0x18, 0x3C, 0x66, 0x66, 0x7E, 0x66, 0x00],
    'B': [0x00, 0x7C, 0x66, 0x7C, 0x66, 0x66, 0x7C, 0x00],
    'E': [0x00, 0x7E, 0x60, 0x7C, 0x60, 0x60, 0x7E, 0x00],
    'I': [0x00, 0x7E, 0x18, 0x18, 0x18, 0x18, 0x7E, 0x00],
    'K': [0x00, 0x66, 0x6C, 0x78, 0x78, 0x6C, 0x66, 0x00],
    'O': [0x00, 0x3C, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
    'P': [0x00, 0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60, 0x00],
    'R': [0x00, 0x7C, 0x66, 0x66, 0x7C, 0x6C, 0x66, 0x00],
    'T': [0x00, 0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00],
    ' ': [0] * 8,
}
LETTERS = {k: [''.join('#' if (b >> (7 - i)) & 1 else '.' for i in range(8)) for b in v]
               for k, v in ATARI_ROM.items()}


def grid():
    ys, xs = np.mgrid[0:H * SS, 0:W * SS]
    return (xs + 0.5) / SS, (ys + 0.5) / SS


def rrect(x, y, x0, y0, x1, y1, r):
    cx = np.clip(x, x0 + r, x1 - r)
    cy = np.clip(y, y0 + r, y1 - r)
    return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1) & \
        ((x - cx) ** 2 + (y - cy) ** 2 <= r * r)


def reel(x, y, cx, cy, angle):
    dx, dy = x - cx, y - cy
    disc = dx * dx + dy * dy <= REEL_R ** 2
    notch = np.zeros_like(disc)
    for k in range(6):
        a = angle + k * math.pi / 3
        ux, uy = math.cos(a), math.sin(a)
        along = dx * ux + dy * uy
        across = -dx * uy + dy * ux
        notch |= (along > REEL_R - 4.3) & (np.abs(across) < 2.1)
    hub = dx * dx + dy * dy <= 3.2 ** 2
    return disc & ~notch & ~hub


X, Y = grid()


def render(angle):
    x, y = X, Y
    ink = rrect(x, y, 2, 2, W - 2, H - 2, 8)                   # black body
    ink &= ~rrect(x, y, 12, 12, W - 12, 80, 3)                 # white label
    (lx, cy), (rx, _) = RC
    pill = ((x >= lx) & (x <= rx) & (np.abs(y - cy) <= PILL_R)) | \
           ((x - lx) ** 2 + (y - cy) ** 2 <= PILL_R ** 2) | ((x - rx) ** 2 + (y - cy) ** 2 <= PILL_R ** 2)
    ink |= pill
    ink &= ~rrect(x, y, 72, 38, 96, 58, 2)                     # center window
    for (cx, cyy) in RC:
        ink &= ~reel(x, y, cx, cyy, angle)
    mid = W / 2

    def trap(inset):                                           # bottom trapezoid
        t = (y - 88) / (H - 2 - 88)
        half_top, half_bot = 42, 47
        hw = half_top + (half_bot - half_top) * t - inset
        return (y >= 88 + inset) & (np.abs(x - mid) <= hw)
    ink &= ~(trap(0) & ~trap(2))
    for hx, hy, hr in ((-36, 102, 3.2), (-23, 99, 2.4), (23, 99, 2.4), (36, 102, 3.2)):
        ink &= ~((x - mid - hx) ** 2 + (y - hy) ** 2 <= hr * hr)
    ink |= ~rrect(x, y, 0, 0, W, H, 10)                        # black outside 2px rim
    cov = ink.reshape(H, SS, W, SS).mean(axis=(1, 3))
    img = (cov >= 0.5).astype(np.uint8)
    # label text, one letter per char cell (rows 0..6, col 7 = spacing)
    for i, ch in enumerate(TEXT):
        for r, line in enumerate(LETTERS[ch]):
            for c, p in enumerate(line):
                if p == '#':
                    img[TEXT_ROW * 8 + r, (TEXT_COL + i) * 8 + c] = 1
    return img


def tile(img, c, r):
    t = img[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
    return bytes(int(''.join(map(str, row)), 2) for row in t)


def reel_tiles(f, col):
    return [tile(f, col + dc, REEL_ROW + dr) for dr in range(RB) for dc in range(RB)]


# render() draws the cassette's black parts as 1. The program shows white ink (COLOR1)
# on black paper (COLOR2), so set pixels are the white parts: invert.
frames = [1 - render(math.radians(60 * i / NFRAMES)) for i in range(NFRAMES)]
for f in frames:
    assert reel_tiles(f, REEL_COLS[0]) == reel_tiles(f, REEL_COLS[1]), "reel blocks differ"
NANIM = RB * RB
ANIM = 64                         # reel character set A
ANIM_B = ANIM + NANIM             # reel character set B, filled at run time
TEXT_CHARS = " -.0123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
STANDARD = {ord(ch) - 32 for ch in TEXT_CHARS}       # standard internal codes
FREE = [c for c in range(1, 128) if c not in STANDARD and not ANIM <= c < ANIM_B + NANIM]
assert set(TEXT) <= set(TEXT_CHARS), "label text uses characters outside the standard set"

anim_frames = [b''.join(reel_tiles(f, REEL_COLS[0])) for f in frames]

screen = np.zeros((24 * 8, 40 * 8), np.uint8)       # black background
screen[CAS_Y * 8:CAS_Y * 8 + H, CAS_X * 8:CAS_X * 8 + W] = frames[0]
free = iter(FREE)
INVERSE = 0x80
SOLID = INVERSE | 0                                 # inverse space: all white
chars = {bytes(8): 0, bytes([255] * 8): SOLID}     # blank = the standard space: black
for ch in sorted(set(TEXT) - {' '}):                 # label letters: black on the white label,
    t = bytes(255 - b for b in ATARI_ROM[ch])       # so the inverse standard letters
    assert t not in chars
    chars[t] = INVERSE | (ord(ch) - 32)
scrfull = []
for r in range(24):
    for c in range(40):
        cr, cc = r - CAS_Y, c - CAS_X
        rc = [rc for rc in REEL_COLS if 0 <= cc - rc < RB]
        if 0 <= cr - REEL_ROW < RB and rc:
            code = ANIM + (cr - REEL_ROW) * RB + (cc - rc[0])
        else:
            t = tile(screen, c, r)
            if t not in chars:
                code = next(free, None)
                if code is None:
                    raise SystemExit(f"the cassette needs more than the {len(FREE)} codes "
                                     f"outside the standard characters and the reel sets")
                chars[t] = code
            code = chars[t]
        scrfull.append(code)
graphics = sorted(c for c in chars.values() if c & 0x7F not in STANDARD)
assert not set(graphics) & STANDARD and not any(ANIM <= c < ANIM_B + NANIM for c in graphics)
print(f'cassette chars: {len(graphics)} graphics of {len(FREE)} free codes, '
      f'{len(chars) - len(graphics)} standard, 2x{NANIM} reel')
font = bytearray(1024)
for t, code in chars.items():
    glyph = bytes(255 - b for b in t) if code & INVERSE else t
    font[(code & 0x7F) * 8:(code & 0x7F) * 8 + 8] = glyph
font[ANIM * 8:(ANIM + NANIM) * 8] = anim_frames[0]

open('Intro.fnt', 'wb').write(font)


def dbytes(data, per=16):
    return '\n'.join('        .byte ' + ','.join(f'${b:02X}' for b in data[i:i + per])
                     for i in range(0, len(data), per))


with open('Intro-Data.asm', 'w') as fh:
    fh.write(f"""; Generated by gen.py - large cassette with label text
; Codes {', '.join(str(c) for c in sorted(STANDARD))} are the standard OS font characters
; " -.0-9:A-Z", copied from the ROM charset at start-up.
CAS_ANIMCHR   = {ANIM}          ; first of {NANIM} animated chars of set A ({RB}x{RB} block, row by row)
CAS_ANIMCHR_B = {ANIM_B}          ; first of {NANIM} animated chars of set B, filled at run time
CAS_ANIMLEN   = {NANIM * 8}        ; bytes copied per animation step
CAS_FRAMESIZE = {NANIM * 8}
CAS_NFRAMES   = {NFRAMES}
CAS_SOLID     = ${SOLID:02X}        ; solid white char: inverse space
CAS_NGRAPHICS = {len(graphics)}          ; other cassette chars, of {len(FREE)} free codes
CAS_X         = {CAS_X}
CAS_Y         = {CAS_Y}
CAS_LABEL_X   = {CAS_X + TEXT_COL}         ; screen position of the label text "{TEXT}"
CAS_LABEL_Y   = {CAS_Y + TEXT_ROW}
CAS_LABEL_LENGTH = {len(TEXT)}

; full 40x24 screen (internal codes)
cas_screen:
""")
    for r in range(24):
        fh.write('        .byte ' + ','.join(f'${v:02X}' for v in scrfull[r * 40:(r + 1) * 40]) + '\n')

# The reel frames are a file of their own, so Intro.asm can place the intro's
# display code between the screen map and the frames.
with open('Intro-Frames.asm', 'w') as fh:
    fh.write(f'; Generated by gen.py - reel frames, {NANIM * 8} bytes each, clockwise order\ncas_frames:\n')
    for i, fr in enumerate(anim_frames):
        fh.write(f'; frame {i}\n' + dbytes(fr) + '\n')

S = 3
imgs = []
for i in range(NFRAMES):
    canvas = np.zeros((192 + 32, 320 + 32), np.uint8)
    for r in range(24):
        for c in range(40):
            code = scrfull[r * 40 + c]
            src = anim_frames[i][(code - ANIM) * 8:(code - ANIM) * 8 + 8] if ANIM <= code < ANIM + NANIM \
                else font[(code & 0x7F) * 8:(code & 0x7F) * 8 + 8]
            if code & INVERSE:
                src = bytes(255 - b for b in src)
            for yy in range(8):
                for xx in range(8):
                    canvas[16 + r * 8 + yy, 16 + c * 8 + xx] = (src[yy] >> (7 - xx)) & 1
    im = Image.fromarray(np.where(canvas, 255, 0).astype(np.uint8))   # white ink on black
    imgs.append(im.resize((im.width * S, im.height * S), Image.NEAREST).convert('P'))
imgs[0].save('preview.gif', save_all=True, append_images=imgs[1:], duration=67, loop=0)
