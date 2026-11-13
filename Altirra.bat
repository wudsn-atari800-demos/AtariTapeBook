@echo off
rem Start Altirra with BASIC and the chapters folder mounted read/write as H:.
rem In BASIC: LOAD "H:C1.BAS" and SAVE "H:C1.BAS"
rem The settings of this Altirra session are not saved.
setlocal
cd /d "%~dp0"
call Make-Settings.bat || exit /b 1
start "Atari Tape Book" Altirra.exe /tempprofile /basic /nocasautoboot /nosiopatch /hdpathrw "%CD%\chapters"
