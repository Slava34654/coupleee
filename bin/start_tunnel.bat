@echo off
cd /d "%~dp0"
cloudflared.exe tunnel --url http://127.0.0.1:8000 >> tunnel.log 2>&1
