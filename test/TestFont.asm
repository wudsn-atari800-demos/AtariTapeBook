

rom_font	= $e000
ram_font	= $3000

porta	= $d302

p1	= $80
p2	= $82
sm	= $d200

	org $2000

start
	mwa #dl $230
	mva #$21 $22f

loop
	lda #8
	sta $d01f
	lda $d01f
	and #1
	asl
	asl
	asl
	ora #$34
	sta porta
	sta 712

	jmp loop
	

	.local dl
:3	.byte $70
:24	.byte $42,a(sm)
	.byte $41,a(dl)
	.endl

	run start
