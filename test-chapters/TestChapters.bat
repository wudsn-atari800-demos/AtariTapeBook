@echo off
rem Runs the end-to-end test of the sync co-track, see TestChapters.py.
setlocal
cd /d "%~dp0"
call ..\Make-Settings.bat || exit /b 1
python TestChapters.py
