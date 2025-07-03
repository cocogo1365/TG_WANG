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

echo "🧪 檢查測試模式環境變量..."
if [ "$TEST_MODE" = "true" ]; then
    echo "✅ 測試模式已啟用"
else
    echo "⚠️  測試模式未啟用，設置 TEST_MODE=true"
    export TEST_MODE=true
fi

echo "🚀 啟動機器人..."
python3 main.py

echo "✅ 機器人重啟完成"