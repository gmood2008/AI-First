#!/bin/bash
# AutoForge 命令包装器 - 自动激活虚拟环境

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行 forge 命令
python3 tools/forge/cli.py "$@"
