@echo off
rem Plays the tape of the last test run in Altirra, at real tape speed like a data recorder.
rem If the tape does not exist yet, TestChapters.py builds and tests it first.
rem The settings of this Altirra session are not saved.
setlocal
cd /d "%~dp0"
call ..\Make-Settings.bat || exit /b 1
if not exist TestChapters.wav python TestChapters.py
if not exist TestChapters.wav exit /b 1
start "Atari Tape Book Test" Altirra.exe /tempprofile /basic /casautoboot /nosiopatch /tape TestChapters.wav
