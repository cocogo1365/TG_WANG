# 🚄 Railway雲端部署指南

## ✅ 您已完成
1. ✅ 安裝Railway CLI
2. ✅ 登入Railway賬戶 (cocogoco@proton.me)

## 🚀 下一步：部署API服務

### 1. 創建Railway項目
```powershell
# 在TG_WANG目錄下執行
cd C:\Users\XX11\Documents\GitHub\TG_WANG
railway init
```

### 2. 選擇部署選項
Railway會詢問：
- 選擇 "Empty Project"
- 項目名稱：輸入 "tg-activation-api" 或您喜歡的名稱

### 3. 部署API服務
```powershell
# 部署簡化版API（推薦）
railway up 簡化雲端API.py

# 或者部署完整版API
railway up 雲端API服務.py
```

### 4. 設置環境變量
```powershell
# 設置API密鑰
railway variables set API_KEY=tg-api-secure-key-2024

# 設置數據庫路徑
railway variables set DB_PATH=bot_database.json
```

### 5. 獲取API地址
```powershell
# 查看部署狀態
railway status

# 獲取公共URL
railway domain
```

## 📋 完整部署流程

現在請按照以下步驟操作：