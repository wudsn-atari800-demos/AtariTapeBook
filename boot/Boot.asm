;
;	@com.wudsn.ide.lng.outputfile=Boot.sec


HATAB_SIZE = 16
START_MOTOR = $34
STOP_MOTOR = $3c

;
BOOT	= $09
RTCLK	= $12
SOUNDR	= $41
SDMCTL	= $22f
COLOR4	= $2c8
HATABS	= $031A
COLDST	= $244
CH	= $2FC
CARTCS	= $bffa
EDITRV	= $e400
SKSTAT	= $d20f
PACTL	= $d302
DMACTL	= $d400
vcount	= $d40b

	opt h-f+

	org $0600      

load_address

	.byte $00	; unused
	.byte 2		; 1 sector
	.word load_address
	.word booter

	mva #STOP_MOTOR PACTL	; Stop tape
	clc
	rts

	nop

basic_loader			; BASIC entry point
	pla
	jmp loader

basic_syncer			; BASIC entry point
	pla
	jmp syncer

	.proc wait
	clc
	adc RTCLK+2
loop	cmp RTCLK+2
	bne loop
	rts
	.endp

	.proc booter
	mva #$00 BOOT
	mva #$00 COLDST
	jsr loader
	jmp (CARTCS)
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

	rts

	.proc read_char
	ldy char_cnt
	bne not_last
	mwa #EDITRV HATABS+7	; Reset HATAB vector for E: handler
not_last
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

