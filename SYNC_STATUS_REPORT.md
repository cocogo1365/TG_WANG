# TG-WANG-BOT 與 TG_WANG 同步狀態報告

## 檢查日期：2025/07/12 20:00

## 概述
- **TG-WANG-BOT**：精簡版Telegram機器人（GitHub: TG-WANG-BOT2）
- **TG_WANG**：完整版系統，包含Web界面（GitHub: TG_WANG）

## 同步狀態

### ✅ 已同步的文件
1. **config.py** - 完全一致
2. **database_adapter.py** - 完全一致
3. **激活碼數據** - 9個激活碼內容相同

### ⚠️ 需要注意的差異

#### 1. bot_database.json
- 內容基本相同，但SHOW1365的使用時間不同
- TG-WANG-BOT: 2025-07-11T21:31:10
- TG_WANG: 2025-07-11T21:25:32

#### 2. main.py
**TG-WANG-BOT版本特點**：
- 有dotenv支援
- 包含完整的激活碼管理功能
- 管理面板有更多按鈕

**TG_WANG版本特點**：
- 較簡潔的實現
- 沒有額外的管理功能

#### 3. activation_codes.py
**TG-WANG-BOT版本**：
- 整合database_adapter
- 支援自定義激活碼
- 會同步到共享數據庫

**TG_WANG版本**：
- 簡單實現
- 沒有數據庫同步功能

## 建議行動

### 1. 決定主要版本
建議以TG_WANG為主版本，因為：
- 功能更完整
- 包含Web界面
- 已部署在Railway

### 2. 同步策略
如果需要保持兩個專案同步：
```bash
# 從TG_WANG複製關鍵文件到TG-WANG-BOT
cp /mnt/c/Users/XX11/Documents/GitHub/TG_WANG/bot_database.json /mnt/c/Users/XX11/Documents/GitHub/TG-WANG-BOT/
cp /mnt/c/Users/XX11/Documents/GitHub/TG_WANG/main.py /mnt/c/Users/XX11/Documents/GitHub/TG-WANG-BOT/
cp /mnt/c/Users/XX11/Documents/GitHub/TG_WANG/activation_codes.py /mnt/c/Users/XX11/Documents/GitHub/TG-WANG-BOT/
```

### 3. 資料共享方案
- 使用PostgreSQL作為中央數據庫
- 兩個專案都使用database_adapter連接
- 確保激活碼數據即時同步

## 目前狀態總結
- 兩個專案基本功能正常
- 核心配置文件已同步
- 激活碼數據大致相同
- 建議統一版本以避免維護困難