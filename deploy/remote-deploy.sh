#!/bin/bash
set -e

cd /var/www/incremental-mcp

echo ">>> 拉取最新代码..."
git pull origin master

echo ">>> 创建/更新虚拟环境..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate

echo ">>> 升级 pip 并安装 Python 依赖..."
pip install --upgrade pip
pip install -e .

echo ">>> 重启服务..."
systemctl restart incremental-mcp

echo ">>> 检查服务状态..."
sleep 2
systemctl status incremental-mcp --no-pager

echo ">>> 部署完成!"
