@echo off
setlocal
cd /d %~dp0\..
if not exist .env (
  copy .env.example .env >nul
  echo [INFO] 已自动创建 .env，请按本机环境检查配置。
)
uv run uvicorn app.main:app --host 0.0.0.0 --port 7982
endlocal
