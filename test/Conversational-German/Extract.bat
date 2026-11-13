@echo off
rem Extracts the Atari BASIC programs from the cassette recording with A8CAS.
setlocal
cd /d "%~dp0"
call ..\..\Make-Settings.bat || exit /b 1
python ExtractTape.py "Conversational GERMAN Unit 1 Side 1.wav" GERMAN1
