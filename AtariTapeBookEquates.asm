;
; Equates of the Atari Tape Book that are not official OS or hardware equates.
; It includes SystemEquates.asm, so a main source file includes only this file.
;

	icl 'SystemEquates.asm'

; OS and hardware values without an official name
CASBUF_DATA = CASBUF+3		; data bytes of the record read by RBLOKV
HATAB_SIZE = 16			; size of a handler vector table, e.g. EDITRV
START_MOTOR = $34		; PACTL value, cassette motor on
STOP_MOTOR = $3C		; PACTL value, cassette motor off

; Memory map, see plans/01_INTRO_DURING_LOADING_PLAN.md
BOOT_LOAD_ADDRESS = $0600	; load address of the boot file (boot/Boot.asm)
INTRO_FONT_ADDRESS = $0800	; the intro's 1K font, directly above the boot record and the intro's display code

; BASIC entry points in the boot file, called by the chapter programs with USR
USR_LOADER = 1550		; X=USR(1550) loads and runs the next chapter
USR_SYNCER = 1554		; X=USR(1554) waits for the next cue of a run section

; Zero page, $CB-$D1 are free for the user
ZP_INTRO_SRC = $CB		; 2 bytes, copy source of the intro
ZP_INTRO_DST = $CD		; 2 bytes, copy destination of the intro
ZP_LOADER_PTR = $CF		; 2 bytes, destination of the pre-loader in the boot file
