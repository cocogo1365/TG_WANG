# 採集數據上傳問題修復指南

## 問題描述
軟體顯示"雲端上傳成功"，但數據沒有出現在網站的採集數據頁面。

## 問題原因
1. 數據結構不匹配 - 軟體和網站使用不同的數據格式
2. API端點可能不正確
3. Railway上的 `uploaded_data` 目錄可能沒有正確創建

## 已完成的修復

### 1. 修復數據顯示邏輯
網站現在支援兩種數據格式：
- 舊格式：`collection_info` 對象
- 新格式：`collections` 數組

### 2. 新增專用上傳API
新增了 `/api/upload_collection_data` 端點，專門處理採集數據上傳。

## 軟體配置建議

### 方案1：使用新的上傳端點
在軟體中配置API端點為：
```
https://tgwang.up.railway.app/api/upload_collection_data
```

請求格式：
```json
{
    "activation_code": "SHOW1365",
    "device_id": "97d0107c8f8d9ba9",
    "device_info": {
        "hostname": "用戶電腦",
        "platform": "Windows 10.0.26100"
    },
    "ip_location": {
        "city": "Pingtung City",
        "country": "Taiwan"
    },
    "group_info": {
        "name": "日本东京大阪风俗情报交流",
        "link": "https://t.me/japanfuzoku"
    },
    "members": [
        {
            "id": 123456,
            "username": "user1",
            "first_name": "用戶1"
        }
        // ... 更多成員
    ]
}
```

### 方案2：檢查uploaded_data目錄
在Railway控制台執行：
```bash
ls -la uploaded_data/
```

如果目錄不存在，創建它：
```bash
mkdir -p uploaded_data
```

## 驗證步驟

1. **檢查Railway日誌**
   查看是否有API請求到達

2. **檢查uploaded_data目錄**
   ```bash
   ls -la uploaded_data/*.json
   ```

3. **手動測試API**
   ```bash
   curl -X POST https://tgwang.up.railway.app/api/upload_collection_data \
     -H "Content-Type: application/json" \
     -d '{"activation_code": "SHOW1365", "members": []}'
   ```

## 臨時解決方案

如果軟體無法修改，可以：
1. 手動上傳JSON文件到 `uploaded_data` 目錄
2. 使用正確的文件名格式：`collection_SHOW1365_1736592000.json`

## 長期解決方案

1. 統一軟體和網站的數據格式
2. 使用PostgreSQL儲存採集數據而不是文件系統
3. 增加錯誤日誌以便調試

更新時間：2025/07/12 20:30