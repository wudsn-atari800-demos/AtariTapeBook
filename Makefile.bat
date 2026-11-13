@echo off
setlocal
cd /d "%~dp0"
call Make-Settings.bat
mads -o:boot/Boot.sec boot/Boot.asm
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/C1.BAS=chapters/C1.WAV chapters/C2.BAS=chapters/C2.WAV AtariTapeBook.wav
Altirra.exe /tempprofile /basic /casautoboot /tape AtariTapeBook.wav
