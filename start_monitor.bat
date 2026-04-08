@echo off
start "SpotifyMonitor" /min powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0monitor_main.ps1"