;
;	@com.wudsn.ide.lng.outputfile=Boot.sec
;
; Boot file of the Atari Tape Book, see plans/01_INTRO_DURING_LOADING_PLAN.md.
;
; The file is a two-stage boot file. Its header announces only the boot
; records (BOOT_RECORDS). The OS loads them and calls load address + 6,
; while the cassette is still open and the motor runs. There, the pre-loader
; stops the motor, fades the boot screen to black and types the title, see
; plans/03_BOOT_FADE_AND_TEXT_PLAN.md. Then it restarts the motor, reads the
; records of the intro (intro/Intro.asm), which follow directly on the tape,
; shows the intro as soon as its display is loaded and starts the animation
; when everything is loaded.
;
; Memory, in this order: the boot records from $0600 (header, BASIC entry
; points, motor control, pre-loader with fade and title), code that runs
; only after everything is loaded, as much as fits below $0800, the intro
; with its font at $0800, and the rest of that code. "booter" raises MEMLO
; above it all, so BASIC's program area starts above it.


	icl '../AtariTapeBookEquates.asm'

	opt h-f+

	org BOOT_LOAD_ADDRESS

load_address

	.byte $00		; unused
	.byte BOOT_RECORDS	; records the OS loads
	.word load_address
	.word booter

	jmp preloader		; called by the OS after the boot records

	.rept 5			; keep the BASIC entry points at USR_LOADER and USR_SYNCER
	nop
	.endr

basic_loader			; BASIC entry point, X=USR(1550[,ADR(T$),LEN(T$)])
	jmp loader_text
	nop

basic_syncer			; BASIC entry point
	pla
	jmp syncer

	.proc motor
start	lda #START_MOTOR	; Start tape
	.byte $2c
stop	lda #STOP_MOTOR	; Stop tape
	sta PACTL
	rts
	.endp

	.proc wait
	clc
	adc RTCLOK+2
loop	cmp RTCLOK+2
	bne loop
	rts
	.endp

; Fade the boot screen to black and type the title, see plan 03.
; Put the character in A with the screen editor's PUT routine. Its address-1 is
; in the editor's handler table in ROM; RTS jumps there, and its RTS returns to
; the caller of put_char.
	.proc put_char
	tax
	lda EDITRV+7
	pha
	lda EDITRV+6
	pha
	txa
	rts
	.endp

	.proc title
FADE_FRAMES = 2			; frames per fade step
TYPE_FRAMES = 2			; frames per typed letter

	ldx #4			; keep the OS colors, the intro restores them in "off"
save_color
	mva COLOR0,x colors,x
	dex
	bpl save_color

fade	ldy #0			; number of colors not yet black
	ldx #4
fade_color
	lda COLOR0,x
	beq next_color		; black already
	iny
	and #$0F
	cmp #3
	bcs darker
	lda #0			; luminance 0 (also after 1 or 2): black, not the dark hue
	beq store_color
darker	lda COLOR0,x		; luminance down by 2, carry is set
	sbc #2
store_color
	sta COLOR0,x
next_color
	dex
	bpl fade_color
	lda #FADE_FRAMES
	jsr wait
	tya
	bne fade
	mva #1 CRSINH		; no cursor
	lda #$7D		; clear the screen
	jsr put_char
	mva #intro.INK COLOR1	; the intro's colors, the others are black already

	mva #intro.CAS_LABEL_Y ROWCRS	; the title, inverse like on the cassette's label
	mva #intro.CAS_LABEL_X COLCRS
	jsr print_text		; leaves text_ptr at the title's terminator, before LOADING
	mva #intro.TEXT_ROW ROWCRS	; LOADING, centered in the intro's text row
	mva #[40-[.len loading_text]]/2 COLCRS

; Print the next zero-terminated text at the cursor, like a typewriter: a key
; click and TYPE_FRAMES to TYPE_FRAMES+7 frames per letter. text_ptr walks
; through the texts, so each call prints the text after the previous one.
; The code above continues here for LOADING.
	.proc print_text
next_char
	inw text_ptr
text_ptr = *+1
	lda title_text-1
	beq text_end
	jsr put_char
	lda #0
	sta CONSOL		; Click
	lda RANDOM
	and #7
	add #TYPE_FRAMES
	jsr wait
	jmp next_char		; wait returns with Z set
text_end
	rts
	.endp

	.local title_text		; ATASCII, inverse
	dta c'ATARI TAPE BOOK'*
	.endl
	.byte 0
	.local loading_text		; ATASCII, follows the title for "type"
	dta c'LOADING'
	.endl
	.byte 0

colors	.ds 5			; COLOR0-COLOR4 before the fade
	.endp

; Second stage: load the intro records that follow the boot records.
	.proc preloader
ptr	= ZP_LOADER_PTR
LAST_BOOT_RECORD = load_address+[BOOT_RECORDS-1]*RECORD_SIZE
MOTOR_START_FRAMES = 25		; about 0.5 s for the motor to reach its speed

	jsr motor.stop		; the tape must not run on while the title is typed
	jsr title
	jsr motor.start
	lda #MOTOR_START_FRAMES
	jsr wait

	ldx #RECORD_SIZE-1	; AltirraOS reads one record more than announced; if the
compare				; original OS does not, the buffer still holds the last boot record
	lda CASBUF_DATA,x
	cmp LAST_BOOT_RECORD,x
	bne have_record
	dex
	bpl compare
	jsr read_record
	bcs fail
have_record
	mwa #load_address+BOOT_RECORDS*RECORD_SIZE ptr
copy_record
	ldy #RECORD_SIZE-1
copy	lda CASBUF_DATA,y
	sta (ptr),y
	dey
	bpl copy
	adw ptr #RECORD_SIZE

	lda shown		; show the intro as soon as its display is loaded
	bne next_record
	lda ptr
	cmp #<intro.display_end
	lda ptr+1
	sbc #>intro.display_end
	bcc next_record
	inc shown
	jsr intro.show
	mva #$00 SOUNDR		; $00 no sound

	ldx #4			; "off" restores the colors from before the fade
pass_color
	mva title.colors,x intro.os_colors,x
	dex
	bpl pass_color
	lda #$7D		; clear the now hidden OS screen with the typed texts,
	jsr put_char		; so BASIC starts on an empty screen with the cursor at home

next_record
	lda ptr
	cmp #<[load_address+TOTAL_RECORDS*RECORD_SIZE]
	lda ptr+1
	sbc #>[load_address+TOTAL_RECORDS*RECORD_SIZE]
	bcs done
	jsr read_record
	bcc copy_record
fail	rts			; carry set: the OS shows BOOT ERROR

done	jsr RBLOKV		; read the end-of-file record, so CLOAD starts at the next file
	jsr intro.start
	clc			; boot continues; motor.stop keeps the carry
	jmp motor.stop

	.proc read_record		; carry set on error
	jsr RBLOKV
	tya
	asl
	rts
	.endp

shown	.byte 0
	.endp

boot_end
BOOT_RECORDS = [boot_end-load_address+RECORD_SIZE-1]/RECORD_SIZE

; Code that runs only after the pre-loader has loaded the whole file: as much
; as fits in front of the intro's font at $0800, the rest behind the intro.
	.proc booter
	mva #2 BOOT?		; cassette boot done: the OS calls CASINI on RESET
	mva #$00 COLDST
	mwa #reset CASINI
	jsr reset
	jsr loader
	jmp (CARTCS)
	.endp

	.proc reset		; protect the intro from BASIC, also after RESET
	mwa #image_end MEMLO
	rts
	.endp

	.proc syncer
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

	icl '../intro/Intro.asm'

; The rest of the code that runs only after everything is loaded.



; USR(1550[,ADR(T$),LEN(T$)]): load and run the next section. The intro shows
; the passed text below the cassette while it loads, or LOADING without
; arguments. Any other number of arguments is treated like none.
	.proc loader_text
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
	jmp loader

length	.byte 0
buffer	.ds intro.TEXT_WIDTH
	.endp

	.proc loader
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

	jmp intro.on		; show the intro while the next file loads

	.proc read_char
	ldy char_cnt
	bne not_last
	mwa #EDITRV HATABS+7	; Reset HATAB vector for E: handler
not_last
	cpy #RUN_INDEX		; CLOAD is done when RUN is typed:
	bne not_run		; the program runs on BASIC's screen
	jsr intro.off
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

	.endp			; loader


image_end			; first free byte, MEMLO
TOTAL_RECORDS = [image_end-load_address+RECORD_SIZE-1]/RECORD_SIZE

	ert basic_loader<>USR_LOADER	; BASIC programs call these addresses
	ert basic_syncer<>USR_SYNCER
	ert intro.font<>INTRO_FONT_ADDRESS	; else the font's alignment wastes memory
	ert [.len title.title_text]<>intro.CAS_LABEL_LENGTH	; the typed title matches the label
