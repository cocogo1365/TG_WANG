# TG旺軟件雲端同步解決方案

## 🎯 問題解決

**問題**: TG機器人生成的激活碼無法被主軟件識別
**原因**: 機器人在Railway雲端運行，激活碼保存在雲端，而主軟件讀取本地資料庫

## ✅ 解決方案

### 1. **軟件激活客戶端** (`software_activation_client.py`)

為TG旺主軟件提供激活碼驗證功能：

```python
from software_activation_client import TGWangActivationClient

# 初始化客戶端
client = TGWangActivationClient()

# 驗證激活碼
result = client.validate_activation_code("6BMLQHT7NGM3TY9J")
if result["valid"]:
    print("激活碼有效")

# 使用激活碼
activation_result = client.use_activation_code("6BMLQHT7NGM3TY9J", "設備ID")
if activation_result["success"]:
    print("激活成功")
```

### 2. **雲端同步** (`cloud_sync_client.py`)

混合驗證系統（優先雲端，本地備用）：

```python
from cloud_sync_client import HybridActivationValidator

validator = HybridActivationValidator()
result = validator.validate_activation_code("激活碼", "設備ID")
```

### 3. **API端點** (已添加到 `integrated_enterprise_app.py`)

- `GET /api/health` - 健康檢查
- `POST /api/verify_activation` - 驗證激活碼
- `POST /api/use_activation` - 使用激活碼
- `POST /sync/activation_code` - 同步激活碼

## 🔄 同步流程

```
TG機器人 (Railway) → 生成激活碼 → 雲端資料庫
                                      ↓
主軟件 ← 雲端API ← 網站後台 ← 讀取雲端資料庫
  ↓
本地資料庫 (備用)
```

## 📋 可用激活碼

目前本地資料庫中的可用激活碼：

| 激活碼 | 類型 | 天數 | 到期時間 | 狀態 |
|--------|------|------|----------|------|
| `6BMLQHT7NGM3TY9J` | trial | 2天 | 2025-07-13 | ✅ 可用 |
| `N7BFM2X8GVHPQW4K` | weekly | 7天 | 2025-07-18 | ✅ 可用 |
| `WEEK7DAYSCODE123` | weekly | 7天 | 2025-12-08 | ✅ 可用 |
| `MONTH30DAYSCODE1` | monthly | 30天 | 2025-12-31 | ✅ 可用 |

## 🚀 如何在主軟件中集成

### 步驟1: 複製激活客戶端

將 `software_activation_client.py` 複製到主軟件目錄

### 步驟2: 集成到主軟件

```python
# 在主軟件中添加
from software_activation_client import TGWangActivationClient

class MainSoftware:
    def __init__(self):
        self.activation_client = TGWangActivationClient()
    
    def check_activation(self):
        # 檢查軟件是否已激活
        pass
    
    def activate_software(self, activation_code):
        result = self.activation_client.use_activation_code(
            activation_code, 
            self.get_device_id()
        )
        return result
```

### 步驟3: 測試激活

```python
# 測試激活碼
software = MainSoftware()
result = software.activate_software("6BMLQHT7NGM3TY9J")
print(result["message"])
```

## 🔧 故障排除

### 問題1: 找不到資料庫檔案
**解決**: 確保 `bot_database.json` 在正確路徑，或設置正確的資料庫路徑

### 問題2: 激活碼無效
**解決**: 
1. 檢查激活碼是否存在於資料庫
2. 檢查激活碼是否已使用
3. 檢查激活碼是否過期

### 問題3: 雲端API連線失敗
**解決**: 系統會自動降級到本地模式，不影響基本功能

## 📊 系統架構

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ TG機器人    │───▶│ Railway雲端   │───▶│ 網站後台     │
│ (生成激活碼) │    │ (機器人部署)  │    │ (API服務)   │
└─────────────┘    └──────────────┘    └─────────────┘
                                             │
                                             ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ TG旺軟件    │◀───│ 激活客戶端    │◀───│ 混合驗證     │
│ (主程序)    │    │ (本地/雲端)   │    │ (本地備用)   │
└─────────────┘    └──────────────┘    └─────────────┘
```

## ✅ 測試結果

- ✅ 本地資料庫連線正常 (9個激活碼)
- ✅ 激活碼驗證功能正常
- ✅ 激活碼使用功能正常
- ⚠️ 雲端API待部署 (目前使用本地模式)

## 📞 支援

如有問題，請檢查：
1. 資料庫檔案路徑是否正確
2. 激活碼是否在有效期內
3. 網路連線是否正常