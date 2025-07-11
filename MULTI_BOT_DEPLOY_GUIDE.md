# TG旺多機器人企業管理系統 🤖

## 🎯 **系統特色**

### ✅ **多機器人支持**
- **主機器人** - 處理主要業務
- **代理商專屬機器人** - 每個代理商有獨立機器人
- **統一管理** - 網站統一管理所有機器人數據
- **數據隔離** - 每個機器人有獨立數據庫

### ✅ **權限分級**
- **超級管理員** - 管理所有機器人和代理商
- **業務經理** - 查看所有數據，管理機器人
- **代理商** - 只能管理自己的機器人和客戶

## 🚀 **部署配置**

### 1. **環境變量設置**

#### **主機器人配置**:
```bash
# 主機器人
BOT_TOKEN=7723514301:AAEya9QRLcAPgmPrTKC5BkAtYWAo8nvKvos
ADMIN_IDS=7537903238
USDT_ADDRESS=TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP
TRONGRID_API_KEY=26af1138-bb1c-446d-81df-b25e957e44db

# 代理商機器人 (最多支持20個)
AGENT_BOT_TOKEN_1=BOT_TOKEN_FOR_AGENT_1
AGENT_ID_1=AGENT001
AGENT_USDT_ADDRESS_1=USDT_ADDRESS_FOR_AGENT_1

AGENT_BOT_TOKEN_2=BOT_TOKEN_FOR_AGENT_2  
AGENT_ID_2=AGENT002
AGENT_USDT_ADDRESS_2=USDT_ADDRESS_FOR_AGENT_2

# Web管理系統
ADMIN_PASSWORD=tgwang2024
MANAGER_PASSWORD=manager123
AGENT_PASSWORD=agent123
```

### 2. **代理商機器人配置文件**

編輯 `agent_bots_config.json`:
```json
{
  "AGENT001": {
    "bot_token": "代理商1的機器人Token",
    "name": "張代理專屬機器人",
    "admin_ids": ["AGENT001", "123456789"],
    "usdt_address": "代理商1的USDT地址",
    "api_key": "TronGrid API Key"
  },
  "AGENT002": {
    "bot_token": "代理商2的機器人Token",
    "name": "李代理專屬機器人", 
    "admin_ids": ["AGENT002", "987654321"],
    "usdt_address": "代理商2的USDT地址",
    "api_key": "TronGrid API Key"
  }
}
```

### 3. **數據庫結構**

系統會自動創建以下數據庫文件：
```
bot_database.json                    # 主機器人數據
bot_database_agent_AGENT001.json    # 代理商1機器人數據  
bot_database_agent_AGENT002.json    # 代理商2機器人數據
uploaded_data/                      # 採集數據目錄
```

## 🖥️ **網站功能展示**

### 📊 **總覽儀表板**
- **聚合統計** - 所有機器人的總收入、訂單、激活碼
- **機器人狀態** - 每個機器人的運行狀態和數據
- **實時監控** - 機器人運行狀態監控

### 🤖 **機器人管理**
```
機器人列表:
├── TG旺主機器人
│   ├── 狀態: 運行中
│   ├── 收入: 1.01 TRX
│   ├── 訂單: 1個
│   └── 激活碼: 8個
├── 張代理專屬機器人 (AGENT001)
│   ├── 狀態: 運行中
│   ├── 收入: 0.5 TRX
│   ├── 訂單: 2個
│   └── 激活碼: 5個
└── 李代理專屬機器人 (AGENT002)
    ├── 狀態: 運行中
    ├── 收入: 0.8 TRX
    ├── 訂單: 3個
    └── 激活碼: 7個
```

### 💼 **訂單管理**
- **統一查看** - 所有機器人的訂單統一顯示
- **機器人過濾** - 按機器人篩選訂單
- **代理商數據** - 代理商只能看自己機器人的訂單

### 🔑 **激活碼管理**
- **跨機器人管理** - 統一管理所有激活碼
- **來源標識** - 清楚顯示激活碼來自哪個機器人
- **狀態追蹤** - 激活碼使用狀態實時更新

### 👥 **代理商管理**
- **專屬機器人分配** - 每個代理商分配專屬機器人
- **業績統計** - 代理商機器人的業績統計
- **權限控制** - 代理商只能管理自己的機器人

## 🔧 **部署步驟**

### 方法1：Railway部署 (推薦)

1. **更新Procfile**:
```
web: python multi_bot_enterprise_app.py
```

2. **推送代碼**:
```bash
git add .
git commit -m "Add multi-bot enterprise system"
git push origin main
```

3. **設置環境變量** (在Railway中):
```bash
# 基本配置
ADMIN_PASSWORD=tgwang2024
BOT_TOKEN=主機器人Token
ADMIN_IDS=7537903238

# 代理商機器人 (根據需要添加)
AGENT_BOT_TOKEN_1=代理商1機器人Token
AGENT_ID_1=AGENT001
```

### 方法2：本地測試

```bash
# 安裝依賴
pip install flask requests

# 運行多機器人系統
python multi_bot_enterprise_app.py

# 訪問網站
http://localhost:5000
```

## 🎯 **使用場景**

### **場景1：單一管理員**
- 使用主機器人處理所有業務
- 通過網站統一管理訂單和激活碼

### **場景2：多代理商模式**
```
總公司 (admin)
├── 管理主機器人
├── 監控所有代理商機器人
└── 查看全局統計

代理商A (AGENT001)
├── 專屬機器人處理客戶
├── 獨立的收入統計
└── 只能管理自己的客戶

代理商B (AGENT002)  
├── 專屬機器人處理客戶
├── 獨立的收入統計
└── 只能管理自己的客戶
```

### **場景3：地區分部**
- 不同地區使用不同機器人
- 統一品牌，分散管理
- 數據隔離，統計聚合

## 🔐 **權限矩陣**

| 功能 | 超級管理員 | 業務經理 | 代理商 |
|-----|---------|---------|-------|
| 查看所有機器人 | ✅ | ✅ | ❌ |
| 管理主機器人 | ✅ | ✅ | ❌ |
| 查看自己機器人 | ✅ | ✅ | ✅ |
| 添加新機器人 | ✅ | ❌ | ❌ |
| 查看所有訂單 | ✅ | ✅ | ❌ |
| 查看自己訂單 | ✅ | ✅ | ✅ |
| 代理商管理 | ✅ | ✅ | ❌ |
| 全局統計 | ✅ | ✅ | ❌ |

## 💡 **最佳實踐**

### **機器人Token管理**
1. 為每個代理商創建專屬機器人
2. 使用不同的USDT接收地址
3. 設置獨立的管理員ID

### **數據備份**
1. 定期備份所有 `bot_database_*.json` 文件
2. 備份 `agent_bots_config.json` 配置
3. 備份 `uploaded_data/` 目錄

### **監控建議**
1. 監控每個機器人的運行狀態
2. 設置收入異常告警
3. 定期檢查數據庫完整性

## 🎉 **部署完成**

部署成功後，您將擁有：
- ✅ 多機器人統一管理
- ✅ 代理商專屬機器人分配
- ✅ 完整的權限控制系統
- ✅ 實時數據監控
- ✅ 聚合統計分析

現在您可以同時運行多個TG機器人，並通過一個網站統一管理所有數據！🚀