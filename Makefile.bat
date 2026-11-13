@echo off
setlocal
cd /d "%~dp0"
call Make-Settings.bat || exit /b 1
mads -o:boot/Boot.sec boot/Boot.asm
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/C1 chapters/C2 AtariTapeBook.wav
Altirra.exe /tempprofile /basic /casautoboot /tape AtariTapeBook.wav
