@echo off
rem Builds the tape AtariTapeBook.wav and starts it in Altirra. Stops at the
rem first step that fails and waits for a key, so the message stays visible.
setlocal
cd /d "%~dp0"
call Make-Settings.bat || goto :failed
mads -o:boot/Boot.bin -t:boot/Boot.lab boot/Boot.asm || goto :failed
rem The boot file with the intro ZX0-compressed, see plans/08_ZX0_INTRO_PLAN.md
python Pack.py boot/Boot.bin boot/Boot.lab boot/Boot.sec || goto :failed
rem The narration while the intro loads, unless there is one (or a recording) already
if not exist boot\Boot.WAV python Speak.py boot\Narration.txt boot\Boot.WAV || goto :failed
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/C1 chapters/C2 AtariTapeBook.wav || goto :failed
Altirra.exe /nosi /tempprofile /basic /casautoboot /nosiopatch /tape AtariTapeBook.wav
exit /b 0

:failed
echo.
echo The build failed, see the message above. Altirra was not started.
pause
exit /b 1
