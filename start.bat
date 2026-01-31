@echo off
REM Trading Noobs Startup Script
REM Double-click to start both backend and frontend

REM Set UTF-8 code page for Chinese characters
chcp 65001 >nul 2>&1

REM Set console font to support UTF-8 (optional, may not work on all systems)
REM reg add "HKCU\Console" /v "FaceName" /t REG_SZ /d "Consolas" /f >nul 2>&1

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start.ps1"
pause
