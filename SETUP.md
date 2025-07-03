# 🚀 TG營銷系統 快速設置指南

## 📋 必需的環境變量

### 1. 設置 Telegram Bot Token
```bash
export BOT_TOKEN="your_telegram_bot_token_here"
```

### 2. 設置 TRON 錢包地址
```bash
export USDT_ADDRESS="your_tron_wallet_address_here"
```

### 3. 設置管理員ID（可選）
```bash
export ADMIN_IDS="123456789,987654321"
```

## 🧪 測試模式啟動

### 方法 1：使用腳本啟動
```bash
./restart_bot.sh
```

### 方法 2：手動啟動
```bash
export TEST_MODE=true
export BOT_TOKEN="your_bot_token"
export USDT_ADDRESS="your_tron_address"
python3 main.py
```

### 方法 3：使用 .env 文件
```bash
# 1. 複製示例文件
cp .env.example .env

# 2. 編輯 .env 文件，填入您的配置
nano .env

# 3. 啟動機器人
python3 main.py
```

## 🧪 測試功能

測試模式啟動後，您應該看到：

1. **主界面新增按鈕**：`🧪 1 TRX 測試購買`
2. **測試流程**：
   - 點擊測試購買按鈕
   - 創建測試訂單（1 TRX + 隨機小數）
   - 點擊"模擬付款測試"
   - 系統發送三條消息：付款確認、激活碼、隨機驗證碼

## ❗ 常見問題

### Q: 沒有看到測試按鈕？
A: 檢查 `TEST_MODE=true` 是否正確設置，並重啟機器人

### Q: 購買後沒收到付款地址？
A: 檢查 `USDT_ADDRESS` 環境變量是否正確設置

### Q: 機器人啟動失敗？
A: 檢查 `BOT_TOKEN` 是否正確設置

## 🔧 調試

運行調試腳本檢查配置：
```bash
python3 test_start.py
```

## 📁 重要文件

- `main.py` - 主程序
- `config.py` - 配置管理
- `database.py` - 數據庫操作
- `restart_bot.sh` - 重啟腳本
- `.env.example` - 配置示例