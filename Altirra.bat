@echo off
rem Start Altirra with BASIC and the chapters folder mounted read/write as H:.
rem In BASIC: LOAD "H:CHAPTER1.BAS" and SAVE "H:CHAPTER1.BAS"
start "" C:\jac\system\Atari800\Tools\EMU\Altirra\Altirra.exe /basic /hdpathrw "%~dp0chapters"
