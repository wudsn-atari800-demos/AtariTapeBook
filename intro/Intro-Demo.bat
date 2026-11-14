@echo off
rem Builds the standalone intro demo (Intro-Demo.asm) and starts it in Altirra.
rem The settings of this Altirra session are not saved.
setlocal
cd /d "%~dp0"
call ..\Make-Settings.bat || exit /b 1
mads Intro-Demo.asm -o:Intro.xex || exit /b 1
start "Atari Tape Book Intro" Altirra.exe /nosi /tempprofile /nobasic /nosiopatch Intro.xex
