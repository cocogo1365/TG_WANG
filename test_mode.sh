#!/bin/bash

# 測試模式啟動腳本
echo "🧪 啟動測試模式..."
echo "📌 使用 1 TRX 進行支付測試"

# 設置測試模式環境變量
export TEST_MODE=true

# 其他必要的環境變量
export BOT_TOKEN="${BOT_TOKEN}"
export USDT_ADDRESS="${USDT_ADDRESS}"
export ADMIN_IDS="${ADMIN_IDS}"

# 啟動機器人
python3 main.py