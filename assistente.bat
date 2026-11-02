@echo off
cd /d "%~dp0"
docker compose up --build -d
if errorlevel 1 (
  echo Nao foi possivel iniciar. Verifique se o Docker Desktop esta em execucao.
  pause
  exit /b 1
)
echo PontoFace iniciado em http://localhost:8000
start http://localhost:8000
pause
