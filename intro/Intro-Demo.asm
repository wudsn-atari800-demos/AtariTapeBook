;
;	@com.wudsn.ide.lng.outputfile=Intro.xex
;
; THE ATARI TAPE BOOK - standalone demo of the intro (Intro.asm)
; Build (MADS):  python3 gen.py
;                mads Intro-Demo.asm -o:Intro.xex

	icl '../AtariTapeBookEquates.asm'

	opt h+

	org $2000		; 1K aligned, so the intro's font starts here

	icl 'Intro.asm'

; The reels follow the motor, so the demo switches it: on for 4 s, off for 2 s.
	.proc start
ON_FRAMES = 200
OFF_FRAMES = 100

	jsr intro.show
	jsr intro.start
loop	mva #START_MOTOR PACTL
	lda #ON_FRAMES
	jsr wait
	mva #STOP_MOTOR PACTL
	lda #OFF_FRAMES
	jsr wait
	jmp loop
	.endp

	.proc wait		; wait A frames
	clc
	adc RTCLOK+2
wait_frame
	cmp RTCLOK+2
	bne wait_frame
	rts
	.endp

	run start
