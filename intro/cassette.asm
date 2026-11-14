;
;	@com.wudsn.ide.lng.outputfile=cassette.xex
;
; THE ATARI TAPE BOOK - intro: animated cassette
; Atari 8-bit, ANTIC mode 2 (GRAPHICS 0), one 1K font for everything
; Build (MADS):  python3 gen.py
;                mads cassette.asm -o:cassette.xex
;
; Cassette 21x14 chars, label text in the Atari ROM font. Both reels share
; the same 16 animated chars; a deferred VBI copies the next 128-byte frame
; into the font every SPEED vertical blanks.

SAVMSC	= $58		; screen memory pointer
CRSINH	= $02F0		; cursor inhibit
COLOR1	= $02C5		; GR.0 text luminance
COLOR2	= $02C6		; GR.0 background
COLOR4	= $02C8		; border
CHBAS	= $02F4		; charset base (page)
SETVBV	= $E45C
XITVBV	= $E462

ptr	= $CB		; free zero page ($CB-$CE)
src	= $CD

SPEED	= 2		; VBIs per animation step (lower = faster)
DIR	= 1		; 1 = clockwise (play), -1 = counter-clockwise (rewind)

	opt h+

	org $2000	; 1K aligned

font	ins 'cassette.fnt'

start	lda #1
	sta CRSINH
	lda #$00		; black ink ...
	sta COLOR1
	sta COLOR4		; black border
	lda #$0E		; white background (only used inside the cassette)
	sta COLOR2
	lda #>font
	sta CHBAS

	.ifdef CAS_NROM
				; copy the label letters from the OS ROM font into our font
	ldx #0
rom_loop
	lda cas_rom_src_lo,x
	sta src
	lda cas_rom_src_hi,x
	sta src+1
	lda cas_rom_dst_lo,x
	sta ptr
	lda cas_rom_dst_hi,x
	sta ptr+1
	ldy #7
rom_char
	lda (src),y
	sta (ptr),y
	dey
	bpl rom_char
	inx
	cpx #CAS_NROM
	bne rom_loop
	.endif

				; copy the 960-byte title screen (title + cassette) to screen memory
	lda SAVMSC
	sta ptr
	lda SAVMSC+1
	sta ptr+1
	lda #<cas_screen
	sta src
	lda #>cas_screen
	sta src+1
	ldx #3			; 3 full pages ...
	ldy #0
copy_page
	lda (src),y
	sta (ptr),y
	iny
	bne copy_page
	inc src+1
	inc ptr+1
	dex
	bne copy_page
copy_rest			; ... + 192 bytes
	lda (src),y
	sta (ptr),y
	iny
	cpy #192
	bne copy_rest

				; install deferred VBI
	lda #7
	ldy #<vbi
	ldx #>vbi
	jsr SETVBV
forever
	jmp forever

; ---------------------------------------------------------------------------
vbi	dec delay
	bne vbi_exit
	lda #SPEED
	sta delay
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
	lda frlo,x
	sta src
	lda frhi,x
	sta src+1
	ldy #CAS_ANIMLEN-1	; max 128 bytes (bpl loop)
copy_frame
	lda (src),y
	sta font+CAS_ANIMCHR*8,y
	dey
	bpl copy_frame
vbi_exit
	jmp XITVBV

; ---------------------------------------------------------------------------
	icl 'cassette_data.s'

frlo
	.rept CAS_NFRAMES
	.byte <(cas_frames+#*CAS_FRAMESIZE)
	.endr
frhi
	.rept CAS_NFRAMES
	.byte >(cas_frames+#*CAS_FRAMESIZE)
	.endr

delay	.byte 1
frame	.byte 0

	run start
