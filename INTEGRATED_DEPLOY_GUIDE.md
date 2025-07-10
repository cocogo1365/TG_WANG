# TG旺企業管理系統 - 機器人數據整合版

## 🎯 整合功能特色

### ✅ 完整數據整合
- **🤖 TG機器人數據** - 自動讀取 `bot_database.json`
- **📊 訂單管理** - 顯示真實的TRX/USDT交易記錄
- **🔑 激活碼系統** - 管理所有激活碼狀態
- **📁 採集數據** - 顯示用戶上傳的採集結果
- **📈 實時統計** - 基於真實數據的統計分析

### 🔗 數據來源
1. **bot_database.json** - TG機器人的訂單、激活碼數據
2. **uploaded_data/** - 用戶採集並上傳的成員數據
3. **實時API** - 與現有TG機器人API完整整合

## 🚀 Railway部署指南

### 方案A：獨立Web服務 (推薦)
```bash
# 1. 更新代碼
git add .
git commit -m "Add integrated enterprise management system"
git push origin main

# 2. Railway部署
# 創建新服務，選擇TG_WANG倉庫
# 設置啟動命令: python integrated_enterprise_app.py
```

### 方案B：與機器人共存
如果想要機器人和Web管理系統同時運行：

1. **修改 Procfile**:
```
web: python integrated_enterprise_app.py
bot: python main.py
api: python app.py
```

2. **環境變量配置**:
```bash
# Web管理系統
PORT=8080
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=tgwang2024

# 數據文件路徑
BOT_DATABASE_PATH=bot_database.json
UPLOAD_DATA_DIR=uploaded_data

# TG機器人 (如果同時運行)
BOT_TOKEN=your-bot-token
ADMIN_IDS=your-admin-ids
USDT_ADDRESS=your-usdt-address
```

## 📱 網站功能展示

### 🏠 儀表板概覽
- **總收入統計** - 顯示TRX/USDT實際收入
- **訂單數量** - 機器人處理的真實訂單
- **激活碼統計** - 已生成/已使用的激活碼
- **採集數據量** - 用戶上傳的成員總數

### 🛒 TG機器人訂單
```json
// 顯示真實數據示例
{
  "order_id": "TG615721W5G6",
  "user_id": 7537903238,
  "plan_type": "weekly",
  "amount": 1.01,
  "currency": "TRX",
  "status": "paid",
  "tx_hash": "386b2300a7518c85...",
  "created_at": "2025-07-04T07:55:00",
  "expires_at": "2025-07-11T16:00:28"
}
```

### 🔑 激活碼管理
- **激活碼狀態** - 已使用/未使用
- **關聯訂單** - 激活碼對應的訂單信息  
- **設備綁定** - 顯示使用激活碼的設備ID
- **到期管理** - 自動檢測過期激活碼

### 📊 採集數據統計
- **採集記錄** - 用戶使用軟件採集的成員數據
- **設備信息** - 採集設備的詳細信息
- **目標群組** - 採集的Telegram群組
- **數據量統計** - 每次採集的成員數量

## 🔧 本地測試

```bash
# 確保有數據文件
ls bot_database.json    # TG機器人數據
ls -la uploaded_data/   # 採集數據目錄

# 安裝依賴
pip install flask requests

# 運行整合系統
python integrated_enterprise_app.py

# 訪問 http://localhost:5000
# 登入: admin/tgwang2024
```

## 📊 數據結構說明

### TG機器人數據 (bot_database.json)
```json
{
  "orders": {
    "訂單ID": {
      "order_id": "訂單編號",
      "user_id": "用戶ID", 
      "plan_type": "方案類型",
      "amount": "金額",
      "currency": "貨幣",
      "status": "狀態",
      "tx_hash": "交易哈希"
    }
  },
  "activation_codes": {
    "激活碼": {
      "activation_code": "激活碼",
      "plan_type": "方案類型",
      "used": "是否已使用",
      "used_by_device": "使用設備"
    }
  },
  "statistics": {
    "total_revenue": "總收入",
    "orders_created": "訂單數量",
    "activations_generated": "激活碼數量"
  }
}
```

### 採集數據 (uploaded_data/*.json)
```json
{
  "activation_code": "激活碼",
  "device_info": {
    "hostname": "設備名稱",
    "platform": "操作系統"
  },
  "collected_members": [
    {
      "username": "用戶名",
      "user_id": "用戶ID",
      "first_name": "名字",
      "phone": "電話",
      "collected_at": "採集時間"
    }
  ],
  "collection_info": {
    "collection_method": "採集方法",
    "target_groups": ["目標群組"],
    "total_collected": "採集數量"
  }
}
```

## 🔐 權限說明

### 管理員 (admin)
- ✅ 查看所有訂單和激活碼
- ✅ 管理所有採集數據
- ✅ 訪問統計分析
- ✅ 用戶管理功能

### 經理 (manager)  
- ✅ 查看訂單和收入統計
- ✅ 管理客戶激活碼
- ✅ 查看採集數據
- ❌ 無系統管理權限

### 代理商 (agent)
- ✅ 查看自己相關的訂單
- ✅ 管理自己客戶的激活碼
- ❌ 無法查看其他代理數據

## 🎉 部署完成後

1. **訪問網站** - Railway提供的域名
2. **檢查數據** - 確認機器人數據正常顯示
3. **測試功能** - 驗證各個模塊正常工作
4. **監控狀態** - 觀察實時數據更新

## 💡 注意事項

- **數據同步** - 網站會實時讀取機器人數據文件
- **文件權限** - 確保Railway環境能讀取數據文件
- **性能優化** - 大量數據時建議啟用緩存
- **安全考慮** - 生產環境請修改默認密碼

現在您有一個完整整合TG機器人數據的企業管理網站！🎊