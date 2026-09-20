@echo off
cd /d "%~dp0..\backend"
"C:\Users\sivak\AppData\Local\Programs\Python\Python312\pythonw.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 >> server.log 2>&1
