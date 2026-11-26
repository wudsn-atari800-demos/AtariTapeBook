;
;	@com.wudsn.ide.lng.mainsourcefile=../boot/Boot.asm
;
; THE ATARI TAPE BOOK - loader: the services the BASIC chapter programs call
;
; Included by boot/Boot.asm behind the intro, see
; plans/05_LOADER_MODULE_PLAN.md. All labels are local to "loader", e.g.
; loader.load. Not to be confused with the boot file's pre-loader, which
; loads the boot file itself and is finished when BASIC starts.
;
; The chapter programs call the entry points through the jump table in
; boot/Boot.asm, whose addresses stay fixed when code moves:
;   load_text  X=USR(2042[,ADR(T$),LEN(T$)]): load and run the next load
;              section, showing T$ or LOADING below the cassette.
;   sync       X=USR(2045): wait for the next cue of a run section.
; booter calls "load" to load the first chapter.
;
; Needs from the boot file: motor, wait, ZP_LOADER_PTR. Needs from the
; intro: turn_on, turn_off, set_text, loading_text, TEXT_WIDTH.

	.local loader

; USR 2042: load and run the next section. The intro shows the passed text
; below the cassette while it loads, or LOADING without arguments. Any other
; number of arguments is treated like none.
	.proc load_text
ptr	= ZP_LOADER_PTR		; free after the pre-loader has finished

	pla			; number of arguments
	cmp #2
	beq text
	tax
	beq default
drop	pla			; drop the arguments
	pla
	dex
	bne drop
default	ldx #<intro.loading_text
	ldy #>intro.loading_text
	lda #.len intro.loading_text
	jmp set

text	pla			; address, high byte first
	sta ptr+1
	pla
	sta ptr
	pla			; length, high byte first
	tax
	pla
	cpx #0
	beq length_low
	lda #255
length_low
	cmp #intro.TEXT_WIDTH+1
	bcc length_ok
	lda #intro.TEXT_WIDTH
length_ok
	sta length
	tay			; copy the text, BASIC may change the string afterwards
	beq copied
copy	dey
	lda (ptr),y
	sta buffer,y
	cpy #0
	bne copy
copied	ldx #<buffer
	ldy #>buffer
	lda length
set	jsr intro.set_text
	jmp load

length	.byte 0
buffer	.ds intro.TEXT_WIDTH
	.endp

; Type CLOAD and RUN through a hook on the E: handler and show the intro
; while the next file loads.
	.proc load
	ldy #HATAB_SIZE-1
copy_loop
	mva EDITRV,Y HATABE,Y
	dey
	bpl copy_loop

	mwa #read_char-1 HATABE+4

	ldx HATABE+6
	ldy HATABE+7
	inx
	bne no_inc_hi
	iny
no_inc_hi
	stx read_char.put_char+1
	sty read_char.put_char+2

	mwa #HATABE HATABS+7	; Change HATAB vector for E: handler
	mva #[.len text]-1 char_cnt

	mva #$12 CH		; Press ENTER
	mva #$00 SOUNDR		; $00 no sound

	jmp intro.turn_on	; show the intro while the next file loads

	.proc read_char
	ldy char_cnt
	bne not_last
	mwa #EDITRV HATABS+7	; Reset HATAB vector for E: handler
not_last
	cpy #RUN_INDEX		; CLOAD is done when RUN is typed:
	bne not_run		; the program runs on BASIC's screen
	jsr intro.turn_off
	ldy char_cnt
not_run
	lda text,Y
	dec char_cnt
	pha
put_char
  	jsr $ffff		; Is initialized to PUTCHR
	pla
	ldy #$01
return	rts
	.endp			; read_char

	.local text
	.byte $9B,'NUR'		; RUN
	.byte $9B,'DAOLC'	; CLOAD
	.endl

RUN_INDEX = 3			; index of the "R" of RUN in text

char_cnt .byte 0
HATABE	.ds HATAB_SIZE

	.endp			; load

; USR 2045: start the motor and wait for the next cue of a run section: the
; serial input changes from 0 to 1 and back, then stop the motor.
	.proc sync
	pla			; number of arguments, none
	jsr motor.start
	lda #50			; Wait 1 s
	jsr wait
	lda #$10		; Mask for the serial input bit
wait_sio_1			; Wait until SIO=1
	bit SKSTAT
	beq wait_sio_1
wait_sio_0			; Wait until SIO=0 again
	bit SKSTAT
	bne wait_sio_0
	jmp motor.stop
	.endp

	.endl
