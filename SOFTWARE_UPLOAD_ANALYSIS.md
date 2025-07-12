# 測試5.py 軟件數據上傳分析

## 軟件日誌分析

根據提供的運行日誌：

### 1. 軟件執行流程
```
✅ 軟件數據上傳客戶端已載入
🔧 開始初始化數據上傳器...
📋 激活碼列表: ['SHOW1365']
🔑 使用激活碼: SHOW1365...
✅ 數據上傳器已啟動
```

### 2. 採集數據
```
[20:17:44] 開始採集活躍用戶，分析最近 50 條消息
[20:17:44] 解析鏈接: https://t.me/japanfuzoku -> japanfuzoku
[20:17:49] 發現 17 個活躍用戶
[20:17:49] 其中 機器人:1 認證用戶:0
[20:17:53] 數據已導出: tg_marketing_data\20250712\活躍用戶_無限制版_japanfuzoku_20250712_201753.xlsx
[後台] 雲端上傳成功: 成功上傳 16 個成員數據
```

## 問題診斷

### 可能的問題原因：

1. **API端點不匹配**
   - 軟件可能使用了錯誤的API端點
   - 或者使用了舊的數據格式

2. **數據存儲位置**
   - 數據可能只存在文件系統，沒有進入PostgreSQL
   - Railway容器的`uploaded_data`目錄可能沒有持久化

3. **數據格式問題**
   - 軟件上傳的格式與網站期望的格式不同

## 解決方案

### 方案1：在Railway執行診斷腳本

1. 將 `check_upload_data.py` 上傳到Railway
2. 在Railway Shell執行：
   ```bash
   python check_upload_data.py
   ```

### 方案2：檢查Railway日誌

在Railway的Deploy Logs中搜索：
- "數據上傳成功"
- "upload_software_data"
- "upload_collection_data"
- "SHOW1365"

### 方案3：手動檢查數據

在Railway Shell執行：
```bash
# 檢查uploaded_data目錄
ls -la uploaded_data/

# 查看最新的上傳文件
ls -lt uploaded_data/*.json | head -5

# 查看文件內容
cat uploaded_data/software_*.json | head -50

# 檢查PostgreSQL
python -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM activation_codes WHERE code = %s', ('SHOW1365',))
print('SHOW1365激活碼:', cur.fetchone())
cur.close()
conn.close()
"
```

## 軟件可能使用的API

根據日誌，軟件可能調用了以下API之一：
1. `/api/upload_software_data` - 舊版API
2. `/api/upload_collection_data` - 新版API（我們剛添加的）
3. 直接寫入文件系統

## 建議的修復步驟

1. **確認上傳目錄存在**
   ```bash
   mkdir -p uploaded_data
   chmod 777 uploaded_data
   ```

2. **檢查API調用日誌**
   在網站代碼中添加日誌：
   ```python
   @app.route('/api/upload_collection_data', methods=['POST'])
   def api_upload_collection_data():
       logger.info(f"收到採集數據上傳請求: {request.remote_addr}")
       # ... 其他代碼
   ```

3. **使用PostgreSQL存儲**
   修改上傳邏輯，直接存入數據庫而不是文件系統

## 驗證數據是否上傳成功

如果數據確實上傳了，應該能看到：
1. `uploaded_data`目錄中有新的JSON文件
2. 文件名包含`SHOW1365`和時間戳
3. 文件內容包含16個採集的成員數據

更新時間：2025/07/12 20:50