#!/usr/bin/env python3
"""
只創建 collection_data 表
"""
import os
import psycopg2

def create_collection_table():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ 錯誤：未設置 DATABASE_URL")
        return False
    
    try:
        print("連接到 PostgreSQL...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 創建 collection_data 表
        print("創建 collection_data 表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS collection_data (
                id SERIAL PRIMARY KEY,
                activation_code VARCHAR(50) NOT NULL,
                device_id VARCHAR(100),
                device_info TEXT,
                ip_location TEXT,
                group_name VARCHAR(255),
                group_link TEXT,
                collection_method VARCHAR(100) DEFAULT '活躍用戶採集',
                members_count INTEGER DEFAULT 0,
                members_data TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 創建索引
        print("創建索引...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_activation_code ON collection_data(activation_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_upload_time ON collection_data(upload_time DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_device_id ON collection_data(device_id)")
        
        conn.commit()
        print("✅ 表創建成功！")
        
        # 驗證表已創建
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'collection_data'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("\n📋 collection_data 表結構：")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}" + (f"({col[2]})" if col[2] else ""))
        
        # 檢查現有的表
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        all_tables = cur.fetchall()
        print("\n📊 數據庫中的所有表：")
        for table in all_tables:
            print(f"  - {table[0]}")
        
        cur.close()
        conn.close()
        
        return True
        
    except psycopg2.errors.DuplicateTable:
        print("✅ collection_data 表已存在")
        return True
        
    except Exception as e:
        print(f"❌ 錯誤：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== 創建採集數據表 ===")
    if create_collection_table():
        print("\n✅ 完成！現在可以開始保存採集數據了。")
    else:
        print("\n❌ 創建失敗，請檢查錯誤信息。")