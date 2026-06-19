#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BACKEND_PORT=8000
FRONTEND_PORT=1420
BACKEND_URL="http://localhost:${BACKEND_PORT}/health"
MAX_RETRIES=30
RETRY_DELAY=2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "  振动监测系统 - 一键启动脚本 (Linux/macOS)"
echo "========================================"
echo ""

echo "[1/3] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误]${NC} 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Python 环境就绪"
echo ""

echo "[2/3] 启动 Python 后端服务..."
cd "${SCRIPT_DIR}/python"

if [ ! -d "venv" ]; then
    echo "正在创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "正在安装依赖..."
pip install -r requirements.txt -q

# 启动后端（后台运行）
uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload &
BACKEND_PID=$!

cd "${SCRIPT_DIR}"

echo ""
echo "等待后端服务启动..."
retry=0
while [ $retry -lt $MAX_RETRIES ]; do
    if curl -s "${BACKEND_URL}" > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} 后端服务已就绪"
        break
    fi
    sleep $RETRY_DELAY
    retry=$((retry + 1))
    elapsed=$((retry * RETRY_DELAY))
    echo "  等待中... (${elapsed}s/$((MAX_RETRIES * RETRY_DELAY))s)"
done

if [ $retry -ge $MAX_RETRIES ]; then
    echo -e "${YELLOW}[警告]${NC} 后端服务启动超时，继续启动前端..."
fi

echo ""
echo "[3/3] 启动前端开发服务器..."
cd "${SCRIPT_DIR}"

if [ ! -d "node_modules" ]; then
    echo "正在安装前端依赖..."
    npm install
fi

# 启动前端（后台运行）
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "  启动完成！"
echo "========================================"
echo ""
echo "  后端 API:   http://localhost:${BACKEND_PORT}"
echo "  前端页面:   http://localhost:${FRONTEND_PORT}"
echo "  API 文档:   http://localhost:${BACKEND_PORT}/docs"
echo ""
echo "  后端 PID:   ${BACKEND_PID}"
echo "  前端 PID:   ${FRONTEND_PID}"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo ""

cleanup() {
    echo ""
    echo "正在停止服务..."
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo "  前端服务已停止"
    fi
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null || true
        echo "  后端服务已停止"
    fi
    echo "所有服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
