@echo off
rem Speaks the narration while the intro loads (Narration.txt) into Boot.WAV,
rem see plans/07_BOOT_NARRATION_PLAN.md. Makefile.bat does it only if Boot.WAV
rem is missing, so run this after changing Narration.txt, then Makefile.bat.
setlocal
cd /d "%~dp0"
call ..\Make-Settings.bat || exit /b 1
python ..\Speak.py Narration.txt Boot.WAV
