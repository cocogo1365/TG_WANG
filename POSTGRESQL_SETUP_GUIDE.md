# PostgreSQL 數據庫設置指南

## Railway PostgreSQL 配置信息

### 內部連接（推薦）
```
DATABASE_URL=postgresql://postgres:KJuMwmpKTPLNteUICkjMoNslsvwxodHa@postgres.railway.internal:5432/railway
```

### 外部連接
```
DATABASE_PUBLIC_URL=postgresql://postgres:KJuMwmpKTPLNteUICkjMoNslsvwxodHa@interchange.proxy.rlwy.net:12086/railway
```

## 在Railway設置環境變量

1. 進入你的TG_WANG服務設置
2. 在Variables部分添加：
   ```
   DATABASE_URL=${{ Postgres.DATABASE_URL }}
   ```

## 創建採集數據表

如果採集數據需要存儲在PostgreSQL中，可以創建以下表結構：

```sql
-- 採集數據表
CREATE TABLE IF NOT EXISTS collection_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info JSONB,
    ip_location JSONB,
    group_name VARCHAR(255),
    group_link TEXT,
    collection_method VARCHAR(100),
    members_count INTEGER,
    members_data JSONB,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX idx_collection_activation_code ON collection_data(activation_code);
CREATE INDEX idx_collection_upload_time ON collection_data(upload_time);
```

## 修改database_adapter.py以支援採集數據

```python
def save_collection_data(self, collection_data):
    """保存採集數據到PostgreSQL"""
    if self.use_postgres:
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO collection_data 
                (activation_code, device_id, device_info, ip_location, 
                 group_name, group_link, collection_method, members_count, members_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                collection_data.get('activation_code'),
                collection_data.get('device_id'),
                json.dumps(collection_data.get('device_info', {})),
                json.dumps(collection_data.get('ip_location', {})),
                collection_data.get('group_name'),
                collection_data.get('group_link'),
                collection_data.get('collection_method'),
                collection_data.get('members_count'),
                json.dumps(collection_data.get('members', []))
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"保存採集數據失敗: {e}")
            return False
    else:
        # 降級到文件存儲
        return self._save_collection_data_to_file(collection_data)

def get_collection_data(self, activation_code=None):
    """從PostgreSQL獲取採集數據"""
    if self.use_postgres:
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if activation_code:
                cur.execute("""
                    SELECT * FROM collection_data 
                    WHERE activation_code = %s 
                    ORDER BY upload_time DESC
                """, (activation_code,))
            else:
                cur.execute("""
                    SELECT * FROM collection_data 
                    ORDER BY upload_time DESC 
                    LIMIT 100
                """)
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            return rows
        except Exception as e:
            self.logger.error(f"獲取採集數據失敗: {e}")
            return []
    else:
        # 降級到文件讀取
        return self._get_collection_data_from_files()
```

## 驗證連接

在Railway的Shell中執行：
```bash
python -c "
import psycopg2
import os

try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute('SELECT version()')
    print('PostgreSQL版本:', cur.fetchone()[0])
    
    # 檢查表
    cur.execute(\"\"\"
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    \"\"\")
    tables = cur.fetchall()
    print('\\n現有表:')
    for table in tables:
        print(f'  - {table[0]}')
    
    cur.close()
    conn.close()
except Exception as e:
    print(f'連接失敗: {e}')
"
```

## 優勢

使用PostgreSQL存儲採集數據的優勢：
1. 可靠性更高
2. 查詢速度更快
3. 支援複雜查詢
4. 自動備份
5. 不依賴文件系統

更新時間：2025/07/12 20:40