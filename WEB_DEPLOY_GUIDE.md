# TG旺企業管理網站 - Railway部署指南

## 🚀 快速部署步驟

### 1. 準備部署文件
已創建的文件：
- `enterprise_web_app.py` - 主要Web應用
- `Procfile.web` - Web服務啟動配置
- `railway-web.json` - Railway專用配置
- `requirements.txt` - 已更新依賴包

### 2. Railway部署選項

#### 選項A：新建Web服務 (推薦)
1. 訪問 [Railway.app](https://railway.app)
2. 連接到您的GitHub TG_WANG倉庫
3. 創建新服務 "TG旺企業管理"
4. 設置環境變量

#### 選項B：在現有項目添加Web服務
1. 在現有Railway項目中點擊 "Add Service"
2. 選擇 "GitHub Repo" 
3. 選擇 TG_WANG 倉庫
4. 配置Web服務

### 3. 環境變量配置

在Railway服務中設置以下環境變量：

```bash
# 基本配置
PORT=8080
SECRET_KEY=your-secret-key-here

# 管理員密碼 (可選，有默認值)
ADMIN_PASSWORD=tgwang2024
MANAGER_PASSWORD=manager123  
AGENT_PASSWORD=agent123

# 數據庫 (Railway會自動提供)
DATABASE_URL=enterprise_management.db
```

### 4. 啟動命令配置

在Railway服務設置中：
- **Start Command**: `python enterprise_web_app.py`
- **Healthcheck Path**: `/`
- **Port**: `$PORT` (自動)

### 5. 自定義域名 (可選)

1. 在Railway服務中點擊 "Settings"
2. 找到 "Domains" 部分
3. 添加自定義域名，例如：
   - `tgwang-admin.your-domain.com`
   - `enterprise.tgwang.com`

## 🔧 本地測試

部署前可以先本地測試：

```bash
# 安裝依賴
pip install flask werkzeug pandas

# 運行應用
python enterprise_web_app.py

# 訪問 http://localhost:5000
```

## 📱 功能特性

### ✅ 完整功能
- **響應式設計** - 支持手機、平板、電腦
- **多用戶權限** - 管理員/經理/代理商
- **實時數據** - 動態更新統計信息
- **現代界面** - Bootstrap 5 + Font Awesome
- **數據可視化** - Chart.js 圖表

### 🎯 權限控制
- **超級管理員** (`admin`): 完整權限
- **業務經理** (`manager`): 收入、客戶、用戶管理
- **代理商** (`agent`): 只能查看自己的客戶和收入

### 📊 核心模塊
1. **儀表板概覽** - 關鍵指標、趨勢圖表
2. **收入統計** - 訂單管理、支付追蹤
3. **客戶管理** - 客戶信息、狀態控制
4. **用戶狀態** - 活動監控、停權管理
5. **代理業務** - 代理商管理、佣金統計
6. **安全監控** - 操作日誌、風險評估

## 🔐 安全特性

- **密碼加密** - SHA256哈希
- **會話管理** - Flask Session
- **權限檢查** - API級別權限驗證
- **操作日誌** - 完整的審計跟蹤
- **數據隔離** - 代理商只能看自己數據

## 📞 技術支持

### 常見問題

**Q: 部署後無法訪問？**
A: 檢查PORT環境變量，確保Railway分配的端口正確

**Q: 登入失敗？**
A: 檢查密碼環境變量，默認：admin/tgwang2024

**Q: 數據不顯示？**
A: 首次部署會自動創建示例數據，刷新頁面即可

**Q: 代理商看不到數據？**
A: 代理商只能看自己相關的數據，確認agent_id匹配

### 部署後訪問

1. **獲取網址**: Railway會提供 `xxx.railway.app` 域名
2. **登入測試**: 使用默認帳號登入
3. **功能驗證**: 測試各模塊功能
4. **數據檢查**: 確認示例數據正常顯示

## 🚀 部署命令

```bash
# 如果使用Railway CLI
railway login
railway link [project-id]
railway up

# 或通過Git推送
git add .
git commit -m "Add enterprise web application"
git push origin main
```

部署完成後，您將擁有一個功能完整的企業級管理網站！

---

**重要提醒**: 
- 生產環境請修改默認密碼
- 建議配置HTTPS域名
- 定期備份數據庫
- 監控系統性能和安全日誌