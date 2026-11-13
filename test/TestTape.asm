

rom_font	= $e000
ram_font	= $3000

p1	= $80
p2	= $82

	org $2000

start
	ldx #0
all_loop
	txa
	sta sm.all,x
:4	mva rom_font+#*$100,x ram_font+#*$100,x	
	inx
	bne all_loop

	mwa #dl $230
;	mwa #>ram_font $2f4

	mwa #char_data p1
	ldx #10
char_loop
	ldy #0
	lda (p1),y
	sta p2
	sty p2+1
	
	asl p2
	rol p2+1
	
	asl p2
	rol p2+1
	
	asl p2
	rol p2+1

	lda #>ram_font
	clc
	adc p2+1
	sta p2+1
	inw p1
	ldy #7
line_loop
	mva (p1),y (p2),y
;	lda $d20a
;	sta (p2),y
	dey
	bpl line_loop
	adw p1 #8
	dex
	bne char_loop

	jmp *
	

	.local dl
:3	.byte $70
	.byte $43,a(sm)
:19	.byte $03
	.byte $41,a(dl)
	.endl
	
	.align $400

	.local sm
	.byte "0123456789012345678901234567890123456789"
	.byte "ABCDEFGHIJKLMNOPQRSTUVWXYZ              "
	.byte "abcdefghijklmnopqrstuvwxyz              "
all	.byte $00
	.endl

	.align $400

char_data
	.byte 12,0,0,0,0,0,24,24,48
	.byte 27,0,0,24,24,0,24,24,48
	.byte 96,48,126,0,0,60,102,12,24
	.byte 103,102,60,0,62,102,102,62,6
	.byte 106,6,60,6,0,31,6,6,6
	.byte 112,96,240,0,124,102,102,124
	.byte 113,6,15,0,62,102,102,62,6
	.byte 121,24,48,0,102,102,102,62,12
	.byte 123,102,60,0,0,126,12,24,12
	.byte 124,126,12,0,0,12,28,60,108

	run start
