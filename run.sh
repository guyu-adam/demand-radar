#!/bin/bash
# 启动需求雷达（守护模式）
# 用法: ./run.sh [间隔分钟数，默认30]

INTERVAL=${1:-30}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "启动需求雷达，间隔 ${INTERVAL} 分钟..."
conda run -n jarves python "$SCRIPT_DIR/demand_radar.py" --interval "$INTERVAL"
