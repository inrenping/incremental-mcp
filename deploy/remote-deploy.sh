#!/bin/bash
set -e

cd /var/www/incremental-mcp

echo ">>> 拉取最新代码..."
git pull origin main

echo ">>> 安装 Python 依赖..."
pip install -e .

echo ">>> 重启服务..."
systemctl restart incremental-mcp

echo ">>> 检查服务状态..."
sleep 2
systemctl status incremental-mcp --no-pager

echo ">>> 部署完成!"
