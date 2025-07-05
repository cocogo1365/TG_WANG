# 🚀 從GitHub部署TG數據管理API

## 📁 文件已準備完成

在您的 `C:\Users\XX11\Documents\GitHub\TG_WANG\` 目錄中，我已經創建了：

1. **`app_with_data_api.py`** - 包含數據管理API的完整服務
2. **`Procfile.data`** - 專用於數據API的啟動配置

## 🚀 GitHub推送和Railway部署步驟

### 步驟1: 提交到GitHub

```bash
# 打開命令提示符
cd C:\Users\XX11\Documents\GitHub\TG_WANG

# 檢查狀態
git status

# 添加新文件
git add app_with_data_api.py
git add Procfile.data
git add GitHub部署指南.md

# 提交
git commit -m "Add data management API with admin dashboard support"

# 推送到GitHub
git push
```

### 步驟2: 在Railway中創建新服務

1. **訪問Railway**: https://railway.com/dashboard
2. **創建新項目或使用現有項目**
3. **添加服務**: 
   - 點擊 "New Service"
   - 選擇 "Deploy from GitHub repo"
   - 選擇您的 `TG_WANG` 倉庫

### 步驟3: 配置服務

#### 3.1 設置啟動命令
- **Start Command**: `python app_with_data_api.py`
- 或者複製 Procfile.data 內容到 Procfile

#### 3.2 設置環境變量
在Railway服務的 "Variables" 標簽中添加：

```
API_KEY=tg-api-secure-key-2024
ADMIN_API_KEY=admin-secure-key-2024
PORT=8000
DB_PATH=bot_database.json
TEST_MODE=true
```

#### 3.3 設置自動部署
- 在 "Settings" → "Source" 中
- 啟用 "Auto Deploy"
- 設置分支為 `main` 或 `master`

### 步驟4: 驗證部署

部署完成後，您會獲得一個URL，例如：
`https://tg-wang-production.up.railway.app`

#### 測試API端點：

```bash
# 1. 健康檢查
curl https://您的URL/health

# 2. 激活碼驗證
curl -X POST https://您的URL/verify \
     -H "Content-Type: application/json" \
     -d '{"activation_code":"2WQ67T9TAVMS9MWR","device_id":"test"}'

# 3. 管理API（這個現在應該正常工作）
curl -H "X-Admin-Key: admin-secure-key-2024" \
     https://您的URL/admin/devices
```

## 🎯 預期結果

成功部署後：

1. **`/health`** 返回：
```json
{
  "status": "healthy",
  "service": "TG營銷系統API",
  "activation_codes": 1,
  "timestamp": "2025-01-04T..."
}
```

2. **`/admin/devices`** 返回：
```json
{
  "devices": [],
  "total": 0,
  "total_records": 0
}
```

而不是 `{"detail":"Not Found"}`

## 📱 使用管理後台

部署成功後，在您的本地電腦運行：

```bash
cd C:\Users\XX11\PythonProject6
python 啟動管理後台.py
```

在管理後台的API設置中，輸入您的Railway URL。

## 🔄 後續更新

以後要更新API功能，只需要：

1. 修改代碼
2. `git add .`
3. `git commit -m "更新說明"`
4. `git push`

Railway會自動檢測到GitHub更新並重新部署！

## 🛡️ 安全考慮

已設置的安全措施：
- API密鑰驗證
- 管理員密鑰分離
- CORS配置
- 錯誤處理和日誌記錄

## ✅ 完成清單

- [x] 創建數據管理API文件
- [x] 設置GitHub部署配置
- [x] 提供完整的部署指南
- [ ] 推送到GitHub
- [ ] 在Railway中配置服務
- [ ] 測試API端點
- [ ] 使用管理後台查看數據