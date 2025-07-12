# 修復測試5.py持續上傳問題

## 問題描述
測試5.py 每5分鐘自動上傳一次數據，導致重複數據過多。

## 問題原因
根據日誌分析，可能的原因：

1. **SoftwareDataUploader 類中有定時上傳功能**
   - 可能在初始化時啟動了後台線程
   - 使用了 Timer 或 while True + sleep(300) 的模式

2. **後台線程持續運行**
   - 日誌顯示 "[後台] 雲端上傳成功"
   - 表明有一個獨立的後台線程在運行

## 修復方案

### 方案1：修改 software_data_uploader.py

在 `C:\Users\XX11\PythonProject6\TG-旺\working_release\software_data_uploader.py` 中查找並修改：

```python
# 查找類似這樣的代碼：
def start_auto_upload(self):
    """開始自動數據上傳"""
    while True:
        try:
            self.upload_data()
            time.sleep(300)  # 5分鐘
        except:
            pass

# 修改為：
def start_auto_upload(self):
    """開始自動數據上傳"""
    # 註釋掉定時上傳
    # while True:
    #     try:
    #         self.upload_data()
    #         time.sleep(300)  # 5分鐘
    #     except:
    #         pass
    pass  # 不做任何事
```

### 方案2：修改測試5.py

在測試5.py中查找並修改：

```python
# 查找類似這樣的代碼：
# 開始自動數據上傳
DATA_UPLOADER = SoftwareDataUploader()
DATA_UPLOADER.start()  # 或 start_auto_upload()

# 修改為：
# 開始自動數據上傳
DATA_UPLOADER = SoftwareDataUploader()
# DATA_UPLOADER.start()  # 註釋掉自動上傳
```

### 方案3：修改上傳邏輯為手動觸發

找到導出數據的函數，確保只在導出時上傳一次：

```python
def export_collected_data(self):
    """導出採集的數據"""
    # ... 導出邏輯 ...
    
    # 只在導出時上傳一次
    if hasattr(self, 'cloud_uploader'):
        try:
            success, message = self.cloud_uploader.upload_collected_data(self.collected_members, collection_info)
            if success:
                print(f"[一次性] 雲端上傳成功: {message}")
        except Exception as e:
            print(f"[一次性] 雲端上傳錯誤: {e}")
    
    # 不要啟動後台線程
    # 刪除或註釋掉類似這樣的代碼：
    # upload_thread = threading.Thread(target=background_upload, daemon=True)
    # upload_thread.start()
```

### 方案4：添加上傳標記

添加一個標記來防止重複上傳：

```python
class DataUploader:
    def __init__(self):
        self.uploaded_data = set()  # 記錄已上傳的數據
    
    def upload_data(self, data_id):
        # 檢查是否已上傳
        if data_id in self.uploaded_data:
            print(f"數據 {data_id} 已上傳，跳過")
            return
        
        # 執行上傳
        # ... 上傳邏輯 ...
        
        # 標記為已上傳
        self.uploaded_data.add(data_id)
```

## 快速修復步驟

1. **找到上傳相關文件**
   ```
   C:\Users\XX11\PythonProject6\TG-旺\working_release\software_data_uploader.py
   C:\Users\XX11\PythonProject6\TG-旺\working_release\測試5.py
   ```

2. **搜索關鍵詞**
   - "300" 或 "5*60" （5分鐘的秒數）
   - "Timer" 或 "timer"
   - "while True"
   - "start_auto_upload"
   - "background"

3. **註釋掉定時上傳代碼**

4. **重啟測試5.py**

## 驗證修復

修復後，運行測試5.py並觀察：
- 應該只在手動導出數據時上傳一次
- 不應該看到每5分鐘的上傳日誌
- 日誌應該顯示 "[一次性] 雲端上傳成功" 而不是 "[後台] 雲端上傳成功"