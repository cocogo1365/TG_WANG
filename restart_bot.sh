#!/bin/bash

echo "🔄 重啟 Telegram 機器人..."

# 停止所有可能的機器人進程
echo "⏹️  停止現有進程..."
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2

# 檢查是否還有進程運行
RUNNING=$(ps aux | grep "python.*main.py" | grep -v grep | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo "⚠️  強制停止殘留進程..."
    pkill -9 -f "python.*main.py" 2>/dev/null || true
    sleep 1
fi

echo "🧪 設置測試模式..."
export TEST_MODE=true

echo "🔍 檢查環境變量..."
echo "TEST_MODE: $TEST_MODE"

# 檢查必需的環境變量
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN 未設置"
    echo "請設置您的 Telegram Bot Token:"
    echo "export BOT_TOKEN='your_bot_token_here'"
    echo ""
    echo "或者創建 .env 文件："
    echo "cp .env.example .env"
    echo "然後編輯 .env 文件填入您的配置"
    exit 1
fi

if [ -z "$USDT_ADDRESS" ]; then
    echo "❌ USDT_ADDRESS 未設置"
    echo "請設置您的 TRON 錢包地址:"
    echo "export USDT_ADDRESS='your_tron_wallet_address'"
    exit 1
fi

echo "✅ BOT_TOKEN: ${BOT_TOKEN:0:10}..."
echo "✅ USDT_ADDRESS: ${USDT_ADDRESS:0:10}..."

echo "🚀 啟動機器人..."
echo "正在使用測試模式啟動..."

# 確保環境變量傳遞給python進程
TEST_MODE=true python3 main.py

echo "✅ 機器人重啟完成"