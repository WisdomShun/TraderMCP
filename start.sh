#!/bin/bash

# TraderMCP 启动脚本

echo "========================================="
echo "  TraderMCP - Interactive Brokers MCP"
echo "========================================="
echo ""

# 检查是否安装了依赖
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "❌ 依赖未安装，正在安装..."
    pip install -e .
fi

# 检查配置文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件"
    echo "正在从模板创建..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
    echo ""
    echo "请编辑 .env 文件，配置IB连接参数："
    echo "  - IB_HOST"
    echo "  - IB_PORT"
    echo "  - IB_ACCOUNT"
    echo ""
    echo "配置完成后，重新运行此脚本"
    exit 1
fi

# 创建必要的目录
mkdir -p data logs

echo "✅ 环境检查完成"
echo ""
echo "启动前请确保："
echo "  1. IB Gateway 或 TWS 已启动"
echo "  2. API 连接已启用"
echo "  3. 端口设置正确"
echo ""
echo "按 Enter 键继续启动服务器，或 Ctrl+C 取消..."
read

echo ""
echo "正在启动 TraderMCP 服务器..."
echo ""

# 启动服务器
python -m src.server
