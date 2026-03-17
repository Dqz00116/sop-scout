#!/bin/bash

# SOP提取工作流一键启动脚本
# 用于WSL2环境 - 适配uv sop虚拟环境
# 用法: bash scripts/start_sop.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/mnt/e/Agent/sop-linux"
ZIP_FILE="/mnt/e/Agent/sop-linux/assets/战争警戒客服-01(3004349308) - 副本.zip"
PORT=5000
SERVICE_URL="http://127.0.0.1:${PORT}"
MAX_WAIT_TIME=60  # 服务启动最大等待时间（秒）

# 切换到项目目录
cd "${PROJECT_DIR}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SOP提取工作流一键启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查Python环境
echo -e "${YELLOW}[1/5] 检查Python环境...${NC}"

# 优先使用当前激活的uv环境
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}错误: 未找到Python${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓ ${PYTHON_VERSION}${NC}"

# 检查必要的依赖
echo -e "${YELLOW}[2/5] 检查Python依赖...${NC}"
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo -e "${RED}错误: 缺少fastapi等依赖${NC}"
    echo -e "${YELLOW}请确保已激活sop环境，或运行: uv pip install -r requirements.txt${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 依赖检查通过${NC}"

# 检查环境变量配置
echo -e "${YELLOW}[3/5] 检查环境配置...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ 找到.env配置文件${NC}"
    # 加载环境变量
    set -a
    source .env
    set +a
else
    echo -e "${YELLOW}警告: 未找到.env文件，请确保已配置环境变量${NC}"
fi

# 检查必要的API Key
if [ -z "$LLM_API_KEY" ]; then
    echo -e "${RED}错误: 未设置LLM_API_KEY环境变量${NC}"
    echo -e "${YELLOW}请在.env文件中设置或手动导出:${NC}"
    echo -e "${YELLOW}  export LLM_API_KEY=your_api_key${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API Key已配置${NC}"

# 检查ZIP文件
echo -e "${YELLOW}[4/5] 检查ZIP文件...${NC}"
if [ ! -f "${ZIP_FILE}" ]; then
    echo -e "${RED}错误: 未找到ZIP文件: ${ZIP_FILE}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ ZIP文件存在: ${ZIP_FILE}${NC}"

# 检查端口是否被占用
echo -e "${YELLOW}[5/5] 检查服务端口...${NC}"
if lsof -i :${PORT} > /dev/null 2>&1; then
    echo -e "${YELLOW}端口 ${PORT} 已被占用，尝试停止现有服务...${NC}"
    bash "${PROJECT_DIR}/scripts/stop_sop.sh" > /dev/null 2>&1
    sleep 2
fi
echo -e "${GREEN}✓ 端口 ${PORT} 可用${NC}"

# 启动HTTP服务
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}启动HTTP服务...${NC}"
nohup $PYTHON_CMD src/main.py -m http -p ${PORT} > /tmp/sop_service.log 2>&1 &
SERVICE_PID=$!
echo -e "${GREEN}✓ 服务已启动 (PID: ${SERVICE_PID})${NC}"

# 等待服务就绪
echo -e "${YELLOW}等待服务就绪...${NC}"
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT_TIME ]; do
    if curl -s "${SERVICE_URL}/" > /dev/null 2>&1; then
        STATUS=$(curl -s "${SERVICE_URL}/" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
        if [ "$STATUS" = "ok" ]; then
            echo -e "${GREEN}✓ 服务已就绪${NC}"
            break
        fi
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done

if [ $WAIT_COUNT -eq $MAX_WAIT_TIME ]; then
    echo ""
    echo -e "${RED}错误: 服务启动超时，请检查日志: /tmp/sop_service.log${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  服务启动成功！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "服务地址: ${SERVICE_URL}"
echo -e "日志文件: /tmp/sop_service.log"
echo ""

# 调用API处理ZIP文件
echo -e "${YELLOW}[开始] 提交SOP提取任务...${NC}"
echo -e "处理文件: ${ZIP_FILE}"
echo ""

# 发送请求
RESPONSE=$(curl -s -X POST "${SERVICE_URL}/run" \
    -H "Content-Type: application/json" \
    -d "{
        \"zip_file\": {
            \"url\": \"${ZIP_FILE}\"
        }
    }")

RUN_ID=$(echo "$RESPONSE" | grep -o '"run_id": "[^"]*"' | cut -d'"' -f4)
STATUS=$(echo "$RESPONSE" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)

if [ -z "$RUN_ID" ]; then
    echo -e "${RED}错误: 任务提交失败${NC}"
    echo -e "${RED}响应: $RESPONSE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 任务已提交${NC}"
echo -e "运行ID: ${RUN_ID}"
echo -e "初始状态: ${STATUS}"
echo ""

# 监控进度
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  任务进度监控${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

LAST_PROGRESS=""
while true; do
    PROGRESS_RESP=$(curl -s "${SERVICE_URL}/progress/${RUN_ID}")
    
    # 解析进度信息
    TOTAL_FILES=$(echo "$PROGRESS_RESP" | grep -o '"total_files": [0-9]*' | awk '{print $2}')
    PROCESSED=$(echo "$PROGRESS_RESP" | grep -o '"processed_files": [0-9]*' | awk '{print $2}')
    EXTRACTED=$(echo "$PROGRESS_RESP" | grep -o '"extracted_sops": [0-9]*' | awk '{print $2}')
    CURRENT_STATUS=$(echo "$PROGRESS_RESP" | grep -o '"status": "[^"]*"' | head -1 | cut -d'"' -f4)
    PROGRESS_PCT=$(echo "$PROGRESS_RESP" | grep -o '"progress_percent": [0-9.]*' | awk '{print $2}')
    
    # 格式化输出
    if [ "$CURRENT_STATUS" = "running" ]; then
        printf "\r${YELLOW}[运行中]${NC} 文件: %s/%s | SOP: %s | 进度: %.1f%%    " \
            "${PROCESSED:-0}" "${TOTAL_FILES:-0}" "${EXTRACTED:-0}" "${PROGRESS_PCT:-0}"
    elif [ "$CURRENT_STATUS" = "completed" ]; then
        echo ""
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  任务完成！${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "处理文件数: ${PROCESSED:-0}/${TOTAL_FILES:-0}"
        echo -e "提取SOP数: ${EXTRACTED:-0}"
        echo ""
        echo -e "输出文件位于: ${PROJECT_DIR}/sop/"
        break
    elif [ "$CURRENT_STATUS" = "error" ]; then
        echo ""
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}  任务执行出错！${NC}"
        echo -e "${RED}========================================${NC}"
        ERROR_MSG=$(echo "$PROGRESS_RESP" | grep -o '"error_message": "[^"]*"' | cut -d'"' -f4)
        echo -e "错误信息: ${ERROR_MSG:-未知错误}"
        exit 1
    elif [ "$CURRENT_STATUS" = "cancelled" ]; then
        echo ""
        echo ""
        echo -e "${YELLOW}========================================${NC}"
        echo -e "${YELLOW}  任务已取消${NC}"
        echo -e "${YELLOW}========================================${NC}"
        break
    fi
    
    sleep 2
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  脚本执行完毕${NC}"
echo -e "${BLUE}========================================${NC}"
