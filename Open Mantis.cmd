@echo off
rem Opens the Mantis site in your browser, starting it first if it is not running.
cd /d "%~dp0"
start "Mantis site" /min python tools\serve.py --open
