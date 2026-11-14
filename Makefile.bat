@echo off
setlocal
cd /d "%~dp0"
call Make-Settings.bat || exit /b 1
mads -o:boot/Boot.sec boot/Boot.asm
rem The narration while the intro loads, unless there is one (or a recording) already
if not exist boot\Boot.WAV python Speak.py boot\Narration.txt boot\Boot.WAV || exit /b 1
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/C1 chapters/C2 AtariTapeBook.wav
Altirra.exe /nosi /tempprofile /basic /casautoboot /nosiopatch /tape AtariTapeBook.wav
