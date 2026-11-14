;
;	@com.wudsn.ide.lng.outputfile=Intro.xex
;
; THE ATARI TAPE BOOK - standalone demo of the intro (Intro.asm)
; Build (MADS):  python3 gen.py
;                mads Intro-Demo.asm -o:Intro.xex

	icl '../SystemEquates.asm'

	opt h+

	org $2000

start	jsr intro.show
	jsr intro.start
	jmp *

	icl 'Intro.asm'

	run start
