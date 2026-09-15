#!/bin/zsh
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
echo "obs-bilibili-live-macos 依赖安装完成。"
