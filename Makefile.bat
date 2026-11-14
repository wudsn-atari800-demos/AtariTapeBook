@echo off
setlocal
cd /d "%~dp0"
call Make-Settings.bat || exit /b 1
mads -o:boot/Boot.bin -t:boot/Boot.lab boot/Boot.asm || exit /b 1
rem The boot file with the intro ZX0-compressed, see plans/08_ZX0_INTRO_PLAN.md
python Pack.py boot/Boot.bin boot/Boot.lab boot/Boot.sec || exit /b 1
rem The narration while the intro loads, unless there is one (or a recording) already
if not exist boot\Boot.WAV python Speak.py boot\Narration.txt boot\Boot.WAV || exit /b 1
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/C1 chapters/C2 AtariTapeBook.wav
Altirra.exe /nosi /tempprofile /basic /casautoboot /nosiopatch /tape AtariTapeBook.wav
