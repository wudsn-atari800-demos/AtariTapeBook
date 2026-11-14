;
;	@com.wudsn.ide.lng.mainsourcefile=Intro-Demo.asm
;
; THE ATARI TAPE BOOK - intro: animated cassette, shown while the tape loads
; Atari 8-bit, ANTIC mode 2 (GRAPHICS 0), one 1K font for everything
;
; Included by boot/Boot.asm, which loads it as the second stage of the boot
; file, and by Intro-Demo.asm, which builds the standalone Intro.xex. All
; labels are local to "intro", e.g. intro.show.
;
; Memory layout, in this order so that the display can be shown before the
; reel frames are loaded:
;   display code and variables, font (1K aligned), display list, screen map
;   and ROM letter table (Intro-Data.asm), reel frames (Intro-Data.asm),
;   animation code, frame table
; The display code is small enough to fit with the boot code below the font
; at $0800, so the font's alignment wastes no memory.
;
; Entry points:
;   show   Save the OS display and show the intro, with the reels standing
;          still. Needs everything up to display_end loaded.
;   start  Copy the label letters from the ROM font and start the reel
;          animation. Needs everything loaded.
;   on     Show the intro again after "off".
;   off    Restore the OS display list, font and colours.
;
; The intro has its own display list and screen memory (the screen map), so
; BASIC's output during loading goes to BASIC's screen and does not show.
; The immediate VBI keeps the intro's display list, font and colours in the
; shadow and hardware registers, because the OS copies the shadows only in
; the deferred VBI, which does not run during serial I/O, and BASIC's start
; reopens the screen.
;
; The animation runs from the immediate VBI, which also runs during tape I/O.
; Before every record, the OS measures the tape speed by polling SKSTAT with
; interrupts enabled, so a VBI longer than one bit (1.67 ms at 600 baud)
; could make the record fail. The VBI therefore copies each frame in two
; chunks into a second set of reel characters (font codes 78-93) while the
; first set (codes 1-16) is shown, and then switches the 32 reel positions
; in the screen map to the other set.

	.local intro

; The OS and hardware equates come from SystemEquates.asm, which the main
; source file includes.

src	= $CB		; free zero page ($CB-$CE), used by show and the VBI
dst	= $CD

SPEED	= 2		; VBIs per animation step, even (lower = faster)
DIR	= 1		; 1 = clockwise (play), -1 = counter-clockwise (rewind)

INK	= $00		; black ink ...
PAPER	= $0E		; ... on white (only used inside the cassette)
BORDER	= $00		; black border

SET_A	= CAS_ANIMCHR	; first char of the reel character set A (in Intro.fnt)
SET_B	= CAS_NCHARS	; first char of the reel character set B (free slots)
CHUNK0	= 48		; bytes copied in the first VBI of a step, which also switches sets
CHUNK1	= CAS_FRAMESIZE-CHUNK0

REEL_ROW = 9		; top row of the two 4x4 reel blocks in the screen map
REEL1_COL = 14
REEL2_COL = 23

; ---------------------------------------------------------------------------
show
on	lda active
	bne on_done
				; save the OS display, to restore it in "off"
	mwa SDLSTL os_dlist
	mva CHBAS os_chbas
	mva COLOR1 os_color1
	mva COLOR2 os_color2
	mva COLOR4 os_color4
	lda #6			; immediate VBI
	ldy #<vbi
	ldx #>vbi
	jsr SETVBV
	mva #1 active
on_done	rts

start	jsr copy_rom_letters	; loaded after the reel frames
	mva #1 animating
	rts

off	lda active
	beq off_done
	lda #6
	ldy #<SYSVBV
	ldx #>SYSVBV
	jsr SETVBV
	mwa os_dlist SDLSTL
	mva os_chbas CHBAS
	mva os_color1 COLOR1
	mva os_color2 COLOR2
	mva os_color4 COLOR4
	mva #0 active
off_done
	rts

; ---------------------------------------------------------------------------
vbi
				; keep the intro on screen; remember a display list or font the OS set meanwhile
	lda SDLSTL
	cmp #<dlist
	bne new_os_dlist
	lda SDLSTL+1
	cmp #>dlist
	beq dlist_ok
new_os_dlist
	mwa SDLSTL os_dlist
	mwa #dlist SDLSTL
dlist_ok
	lda CHBAS
	cmp #>font
	beq font_ok
	sta os_chbas
	mva #>font CHBAS
font_ok
	mwa #dlist DLISTL
	mva #>font CHBASE
	lda #INK
	sta COLOR1
	sta COLPF1
	lda #PAPER
	sta COLOR2
	sta COLPF2
	lda #BORDER
	sta COLOR4
	sta COLBK
	lda #$22		; normal playfield, display list DMA
	sta SDMCTL
	sta DMACTL
	lda #0
	sta ATRACT
	lda animating
	beq vbi_exit
	jmp animate		; loaded after the reel frames
vbi_exit
	jmp SYSVBV

; Variables, loaded with the code because "show" already uses them
active		.byte 0		; VBI installed
animating	.byte 0		; reel frames and animation code loaded
delay		.byte 1
phase		.byte 0		; 0 = first chunk of a step, 1 = second chunk
complete	.byte 0		; the hidden set holds a complete frame
frame		.byte 0		; frame shown or being copied
visible_set	.byte 0		; 0 = set A, 1 = set B
base		.byte 0
os_dlist	.word 0
os_chbas	.byte 0
os_color1	.byte 0
os_color2	.byte 0
os_color4	.byte 0

; ---------------------------------------------------------------------------
	.align $400

font	ins 'Intro.fnt'

dlist	.byte $70,$70,$70
	.byte $42,<cas_screen,>cas_screen
	.rept 23
	.byte $02
	.endr
	.byte $41,<dlist,>dlist

	icl 'Intro-Data.asm'

display_end = cas_frames	; everything "show" needs lies below

; ---------------------------------------------------------------------------
; Animation part of the VBI, needed only after the reel frames are loaded.
animate
	dec delay
	bne anim_exit
	mva #SPEED/2 delay
	lda phase
	bne second_chunk

				; first VBI of a step: show the completed set, copy the first chunk of the next frame
	lda complete
	beq no_switch
	jsr switch_sets
	mva #0 complete
no_switch
	ldx frame
	.if DIR > 0
	inx
	cpx #CAS_NFRAMES
	bcc frame_ok
	ldx #0
	.else
	dex
	bpl frame_ok
	ldx #CAS_NFRAMES-1
	.endif
frame_ok
	stx frame
	jsr set_pointers
	ldy #CHUNK0-1
copy_chunk0
	lda (src),y
	sta (dst),y
	dey
	bpl copy_chunk0
	mva #1 phase
	jmp SYSVBV

second_chunk			; second VBI of a step: copy the rest of the frame
	ldx frame
	jsr set_pointers
	adw src #CHUNK0
	adw dst #CHUNK0
	ldy #CHUNK1-1
copy_chunk1
	lda (src),y
	sta (dst),y
	dey
	bpl copy_chunk1
	mva #0 phase
	mva #1 complete
anim_exit
	jmp SYSVBV

; Copy the label letters from the OS ROM font into our font. Intro.fnt already
; holds them as in the ROM, so the label shows correctly before this runs.
copy_rom_letters
	.ifdef CAS_NROM
				; copy the label letters from the OS ROM font into our font
	ldx #0
rom_loop
	lda cas_rom_src_lo,x
	sta src
	lda cas_rom_src_hi,x
	sta src+1
	lda cas_rom_dst_lo,x
	sta dst
	lda cas_rom_dst_hi,x
	sta dst+1
	ldy #7
rom_char
	lda (src),y
	sta (dst),y
	dey
	bpl rom_char
	inx
	cpx #CAS_NROM
	bne rom_loop
	.endif
	rts

; Set src to frame X and dst to the hidden reel character set.
set_pointers
	lda frlo,x
	sta src
	lda frhi,x
	sta src+1
	lda visible_set
	bne hidden_a
	mwa #font+SET_B*8 dst
	rts
hidden_a
	mwa #font+SET_A*8 dst
	rts

; Show the other reel character set in both reel blocks.
switch_sets
	lda visible_set
	eor #1
	sta visible_set
	beq show_a
	lda #SET_B
	bne set_base
show_a	lda #SET_A
set_base
	sta base
	ldx #15
switch_loop
	ldy reel_offsets,x
	txa
	clc
	adc base
	sta reel1,y
	sta reel2,y
	dex
	bpl switch_loop
	rts

reel_offsets			; offsets of the 16 reel chars from the top left of a block
	.rept 16
	.byte [#/4]*40+[#%4]
	.endr


reel1	= cas_screen+REEL_ROW*40+REEL1_COL
reel2	= cas_screen+REEL_ROW*40+REEL2_COL

frlo
	.rept CAS_NFRAMES
	.byte <(cas_frames+#*CAS_FRAMESIZE)
	.endr
frhi
	.rept CAS_NFRAMES
	.byte >(cas_frames+#*CAS_FRAMESIZE)
	.endr

end				; first free byte after the intro

	ert CAS_ANIMLEN<>CAS_FRAMESIZE	; the VBI copies whole frames
	ert SET_B+16>128		; set B must fit into the font
	ert (cas_screen&$F000)<>((cas_screen+959)&$F000)	; screen memory must not cross 4K
	ert (dlist&$FC00)<>((dlist+31)&$FC00)			; display list must not cross 1K

	.endl
