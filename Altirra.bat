@echo off
rem Start Altirra with BASIC and the chapters folder mounted read/write as H:.
rem In BASIC: LOAD "H:C1.BAS" and SAVE "H:C1.BAS"
setlocal
cd /d "%~dp0"
call Make-Settings.bat
start "Atari Tape Book" Altirra.exe /basic /nocasautoboot /hdpathrw "%CD%\chapters"
