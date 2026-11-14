;
;	@com.wudsn.ide.lng.outputfile=Boot.sec
;
; Boot file of the Atari Tape Book, see plans/01_INTRO_DURING_LOADING_PLAN.md.
;
; The file is a two-stage boot file. Its header announces only the boot
; records (BOOT_RECORDS). The OS loads them and calls load address + 6,
; while the cassette is still open and the motor runs. There, the pre-loader
; reads the records of the intro (intro/Intro.asm), which follow directly on
; the tape, shows the intro as soon as its display is loaded and starts the
; animation when everything is loaded.
;
; Memory, in this order: the boot records from $0600 (header, BASIC entry
; points, pre-loader), the intro with its font at $0800, and the code that
; runs only after everything is loaded (init routine, CLOAD/RUN typing, BASIC
; syncer). "booter" raises MEMLO above it all, so BASIC's program area
; starts above it.


HATAB_SIZE = 16
START_MOTOR = $34
STOP_MOTOR = $3c

	icl '../SystemEquates.asm'

CASBUF_DATA = CASBUF+3	; data bytes of the record read by RBLOKV

	opt h-f+

	org $0600

load_address

	.byte $00		; unused
	.byte BOOT_RECORDS	; records the OS loads
	.word load_address
	.word booter

	jmp preloader		; called by the OS after the boot records

	.rept 5			; keep the BASIC entry points at 1550 and 1554
	nop
	.endr

basic_loader			; BASIC entry point
	pla
	jmp loader

basic_syncer			; BASIC entry point
	pla
	jmp syncer

; Second stage: load the intro records that follow the boot records.
	.proc preloader
ptr	= $CF			; free zero page, the intro uses $CB-$CE
LAST_BOOT_RECORD = load_address+[BOOT_RECORDS-1]*128

	ldx #127		; AltirraOS reads one record more than announced; if the
compare				; original OS does not, the buffer still holds the last boot record
	lda CASBUF_DATA,x
	cmp LAST_BOOT_RECORD,x
	bne have_record
	dex
	bpl compare
	jsr read_record
	bcs fail
have_record
	mwa #load_address+BOOT_RECORDS*128 ptr
copy_record
	ldy #127
copy	lda CASBUF_DATA,y
	sta (ptr),y
	dey
	bpl copy
	adw ptr #128

	lda shown		; show the intro as soon as its display is loaded
	bne next_record
	lda ptr
	cmp #<intro.display_end
	lda ptr+1
	sbc #>intro.display_end
	bcc next_record
	inc shown
	jsr intro.show

next_record
	lda ptr
	cmp #<[load_address+TOTAL_RECORDS*128]
	lda ptr+1
	sbc #>[load_address+TOTAL_RECORDS*128]
	bcs done
	jsr read_record
	bcc copy_record
fail	rts			; carry set: the OS shows BOOT ERROR

done	jsr RBLOKV		; read the end-of-file record, so CLOAD starts at the next file
	jsr intro.start
	mva #STOP_MOTOR PACTL	; Stop tape
	clc
	rts

read_record			; carry set on error
	jsr RBLOKV
	tya
	asl
	rts

shown	.byte 0
	.endp

boot_end
BOOT_RECORDS = [boot_end-load_address+127]/128

	icl '../intro/Intro.asm'

; Third part: everything that runs only after the pre-loader has loaded the
; whole file: the init routine, the CLOAD/RUN typing and the BASIC syncer.
	.proc wait
	clc
	adc RTCLOK+2
loop	cmp RTCLOK+2
	bne loop
	rts
	.endp

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

	.proc syncer
	mva #START_MOTOR PACTL
	lda #50			; Wait 1 s
	jsr wait
	lda #$10		; Mask for the serial input bit
wait_sio_1			; Wait until SIO=1
	bit SKSTAT
	beq wait_sio_1
wait_sio_0			; Wait until SIO=0 again
	bit SKSTAT
	bne wait_sio_0
	mva #STOP_MOTOR PACTL
	rts
	.endp

image_end			; first free byte, MEMLO
TOTAL_RECORDS = [image_end-load_address+127]/128

	ert basic_loader<>1550		; BASIC programs call these addresses
	ert basic_syncer<>1554
	ert intro.font<>$0800		; else the font's alignment wastes memory
