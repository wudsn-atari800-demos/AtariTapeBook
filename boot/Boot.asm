;
;	@com.wudsn.ide.lng.outputfile=Boot.sec
;
; Boot file of the Atari Tape Book, see plans/01_INTRO_DURING_LOADING_PLAN.md
; and plans/04_SMALLER_BOOT_PLAN.md.
;
; The file is a two-stage boot file. Its header announces only the boot
; record (BOOT_RECORDS). The OS loads it and calls the pre-loader at load
; address + 6, while the cassette is still open and the motor runs. The
; pre-loader reads the following records itself: first the second stage with
; the title code, then the intro (intro/Intro.asm). As soon as the title code
; is loaded (PAUSE_ADDRESS), it pauses: it stops the motor, fades the boot
; screen to black, types the title (plans/03_BOOT_FADE_AND_TEXT_PLAN.md) and
; restarts the motor. It shows the intro as soon as its display is loaded and
; starts the animation when everything is loaded.
;
; Memory, in this order: the boot record from $0600 (header, pre-loader), the
; second stage up to $0800 (the code the pause needs first, then the code that
; runs after loading, and the jump table with the BASIC entry points at the
; end), the intro with its font at $0800 (intro/Intro.asm), and the services
; the BASIC chapters call (loader/Loader.asm, plans/05_LOADER_MODULE_PLAN.md).
; "booter" raises MEMLO above it all, so BASIC's program area starts above it.
;
; The first header byte, which the OS ignores for cassette boot, holds the
; record after which the pre-loader pauses (PAUSE_RECORD). Bin2Wav.py extends
; the gap after that record, so the restarted motor reaches its speed before
; the next record.

	icl '../AtariTapeBookEquates.asm'

	opt h-f+

	org BOOT_LOAD_ADDRESS

load_address

	.byte PAUSE_RECORD	; ignored by the OS, read by Bin2Wav.py
	.byte BOOT_RECORDS	; records the OS loads
	.word load_address
	.word booter

; First stage, called by the OS at load address + 6 after the boot record:
; read the records that follow.
	.proc preloader
ptr	= ZP_LOADER_PTR
LAST_BOOT_RECORD = load_address+[BOOT_RECORDS-1]*RECORD_SIZE

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

	lda ptr+1		; pause when the title code is loaded
	ldx ptr
	cpx #<PAUSE_ADDRESS
	bne no_pause
	cmp #>PAUSE_ADDRESS
	bne no_pause
	jsr pause
	jmp next_record
no_pause
	cpx #<SHOW_ADDRESS	; show the intro when its display is loaded
	bne next_record
	cmp #>SHOW_ADDRESS
	bne next_record
	jsr show_intro

next_record
	lda ptr
	cmp #<[load_address+TOTAL_RECORDS*RECORD_SIZE]
	lda ptr+1
	sbc #>[load_address+TOTAL_RECORDS*RECORD_SIZE]
	bcc read_next
	jmp finish		; all records are loaded
read_next
	jsr read_record
	bcc copy_record
fail	rts			; carry set: the OS shows BOOT ERROR

	.proc read_record		; carry set on error
	jsr RBLOKV
	tya
	asl
	rts
	.endp
	.endp

boot_end
BOOT_RECORDS = [boot_end-load_address+RECORD_SIZE-1]/RECORD_SIZE

; Second stage, read by the pre-loader. The code the pause needs comes first,
; so the pause, and with it the title, comes as early as possible.

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

; Fade the boot screen to black and type the title, see plan 03.
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
	mva #$00 SOUNDR		; no data noise when the loading continues
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

; Stop the motor, fade the screen, type the title, restart the motor.
	.proc pause
MOTOR_START_FRAMES = 25		; about 0.5 s for the motor to reach its speed

	jsr motor.stop		; the tape must not run on while the title is typed
	jsr title
	jsr motor.start
	lda #MOTOR_START_FRAMES
	jmp wait
	.endp

pause_end
PAUSE_RECORD = [pause_end-load_address+RECORD_SIZE-1]/RECORD_SIZE
PAUSE_ADDRESS = load_address+PAUSE_RECORD*RECORD_SIZE

; Code that runs only after the pause or after loading.

; Called when the intro's display is loaded.
	.proc show_intro
	jsr intro.show

	ldx #4			; "off" restores the colors from before the fade
pass_color
	mva title.colors,x intro.os_colors,x
	dex
	bpl pass_color
	lda #$7D		; clear the now hidden OS screen with the typed texts,
	jmp put_char		; so BASIC starts on an empty screen with the cursor at home
	.endp

SHOW_ADDRESS = load_address+[[intro.display_end-load_address+RECORD_SIZE-1]/RECORD_SIZE]*RECORD_SIZE

; Called when all records are loaded; returns to the OS.
	.proc finish
	jsr RBLOKV		; read the end-of-file record, so CLOAD starts at the next file
	jsr intro.start
	clc			; boot continues; motor.stop keeps the carry
	jmp motor.stop
	.endp

	.proc booter
	mva #2 BOOT?		; cassette boot done: the OS calls CASINI on RESET
	mva #$00 COLDST
	mwa #reset CASINI
	jsr reset
	jsr loader.load		; load the first chapter
	jmp (CARTCS)
	.endp

	.proc reset		; protect the intro from BASIC, also after RESET
	mwa #image_end MEMLO
	rts
	.endp

; BASIC entry points at fixed addresses directly below the intro's font, so
; they stay in place when code moves.
	ert *>USR_LOADER
	org USR_LOADER
basic_loader			; X=USR(2042[,ADR(T$),LEN(T$)])
	jmp loader.load_text
basic_syncer			; X=USR(2045)
	jmp loader.sync

	icl '../intro/Intro.asm'

	icl '../loader/Loader.asm'

image_end			; first free byte, MEMLO
TOTAL_RECORDS = [image_end-load_address+RECORD_SIZE-1]/RECORD_SIZE

	ert basic_loader<>USR_LOADER	; BASIC programs call these addresses
	ert basic_syncer<>USR_SYNCER
	ert intro.font<>INTRO_FONT_ADDRESS	; else the font's alignment wastes memory
	ert [.len title.title_text]<>intro.CAS_LABEL_LENGTH	; the typed title matches the label
	ert PAUSE_RECORD<=BOOT_RECORDS	; the pre-loader reads the title code itself
	ert SHOW_ADDRESS<=PAUSE_ADDRESS
