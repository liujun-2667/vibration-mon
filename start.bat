@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   振动监测系统 - 一键启动脚本 (Windows)
echo ========================================
echo.

set BACKEND_PORT=8000
set FRONTEND_PORT=1420
set BACKEND_URL=http://localhost:%BACKEND_PORT%/health
set MAX_RETRIES=30
set RETRY_DELAY=2

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 环境就绪
echo.

echo [2/3] 启动 Python 后端服务...
cd /d "%~dp0python"

if not exist "venv" (
    echo 正在创建 Python 虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo 正在安装依赖...
pip install -r requirements.txt -q

start "Vibration Backend" cmd /k "uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

cd /d "%~dp0"

echo.
echo 等待后端服务启动...
set retry=0
:wait_backend
if %retry% geq %MAX_RETRIES% (
    echo [警告] 后端服务启动超时，继续启动前端...
    goto start_frontend
)

ping -n %RETRY_DELAY% 127.0.0.1 >nul

curl -s %BACKEND_URL% >nul 2>&1
if not errorlevel 1 (
    echo [OK] 后端服务已就绪
    goto start_frontend
)

set /a retry+=1
set /a elapsed=retry*RETRY_DELAY
echo   等待中... (%elapsed%s/%MAX_RETRIES%*%RETRY_DELAY%s)
goto wait_backend

:start_frontend
echo.
echo [3/3] 启动前端开发服务器...
cd /d "%~dp0"

if not exist "node_modules" (
    echo 正在安装前端依赖...
    call npm install
)

start "Vibration Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo   后端 API:   http://localhost:%BACKEND_PORT%
echo   前端页面:   http://localhost:%FRONTEND_PORT%
echo   API 文档:   http://localhost:%BACKEND_PORT%/docs
echo.
echo   按 Ctrl+C 可停止本脚本
echo   如需停止服务，请关闭对应的命令行窗口
echo.
pause
