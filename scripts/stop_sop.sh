#!/bin/bash

# SOP提取工作流一键停止脚本
# 用于WSL2环境
# 用法: bash scripts/stop_sop.sh

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SOP提取工作流停止脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 查找SOP服务进程
echo -e "${YELLOW}[1/2] 查找SOP服务进程...${NC}"

# 查找包含main.py的Python进程
PIDS=$(ps aux | grep "src/main.py" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo -e "${YELLOW}未找到运行中的SOP服务进程${NC}"
else
    echo -e "${GREEN}找到以下进程:${NC}"
    for PID in $PIDS; do
        ps -p $PID -o pid,cmd | tail -1
    done
fi

echo ""

# 停止进程
echo -e "${YELLOW}[2/2] 停止服务进程...${NC}"

STOPPED_COUNT=0
if [ -n "$PIDS" ]; then
    for PID in $PIDS; do
        echo -e "正在停止进程: ${PID}..."
        
        # 先尝试优雅终止 (SIGTERM)
        kill $PID 2>/dev/null
        
        # 等待进程退出
        WAIT_COUNT=0
        while [ $WAIT_COUNT -lt 5 ]; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
            WAIT_COUNT=$((WAIT_COUNT + 1))
        done
        
        # 如果还在运行，强制终止 (SIGKILL)
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}进程未响应，强制终止...${NC}"
            kill -9 $PID 2>/dev/null
        fi
        
        if ! ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 进程 ${PID} 已停止${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
        else
            echo -e "${RED}✗ 无法停止进程 ${PID}${NC}"
        fi
    done
fi

echo ""
echo -e "${BLUE}========================================${NC}"

if [ $STOPPED_COUNT -gt 0 ]; then
    echo -e "${GREEN}  成功停止 ${STOPPED_COUNT} 个服务进程${NC}"
elif [ -n "$PIDS" ]; then
    echo -e "${YELLOW}  部分进程未能停止，请手动检查${NC}"
else
    echo -e "${YELLOW}  没有运行中的服务需要停止${NC}"
fi

echo -e "${BLUE}========================================${NC}"

# 额外检查端口占用情况
echo ""
echo -e "${YELLOW}[额外检查] 检查端口5000占用情况...${NC}"
PORT_PIDS=$(lsof -i :5000 -t 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo -e "${YELLOW}端口5000仍被以下进程占用:${NC}"
    lsof -i :5000
    echo ""
    echo -e "${YELLOW}是否强制释放端口? (y/N)${NC}"
    read -r -t 5 RESPONSE || RESPONSE="n"
    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        for P in $PORT_PIDS; do
            kill -9 $P 2>/dev/null && echo -e "${GREEN}✓ 已终止进程 ${P}${NC}"
        done
    fi
else
    echo -e "${GREEN}✓ 端口5000已释放${NC}"
fi

echo ""
