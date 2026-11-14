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

start	jsr intro.show
	jsr intro.start
	jmp *

	run start
