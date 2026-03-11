#!/bin/bash

# ==========================================
# 记忆熔炉 (MemoryForge) 一键启动脚本
# 功能：清理端口、执行数据库迁移、启动服务
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}>>> 准备启动记忆熔炉 (MemoryForge)...${NC}"

# 1. 检查并清理被占用的 8000 端口
PORT=8000
PID=$(lsof -t -i:$PORT)

if [ -n "$PID" ]; then
    echo -e "${YELLOW}>>> 发现端口 $PORT 正在被 PID $PID 占用，正在结束该进程...${NC}"
    kill -9 $PID
    sleep 1
    echo -e "${GREEN}>>> 端口 $PORT 已释放。${NC}"
else
    echo -e "${GREEN}>>> 端口 $PORT 未被占用。${NC}"
fi

# 2. 执行数据库迁移 (解决 unapplied migration 警告)
echo -e "${GREEN}>>> 正在应用数据库迁移...${NC}"
python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}>>> 数据库迁移失败，请检查错误信息！${NC}"
    exit 1
fi

# 3. 确保 static 目录存在
mkdir -p static

# 4. 启动 Django 服务
echo -e "${GREEN}>>> 正在启动 Django 服务...${NC}"
echo -e "${GREEN}>>> 请在浏览器访问: http://127.0.0.1:$PORT${NC}"
python manage.py runserver 0.0.0.0:$PORT
