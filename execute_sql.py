#!/usr/bin/env python3
"""
執行 SQL 創建表
"""
import os
import psycopg2

def execute_sql():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("錯誤：未設置 DATABASE_URL")
        return
    
    sql_commands = """
-- 創建 collection_data 表
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
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_collection_activation_code ON collection_data(activation_code);
CREATE INDEX IF NOT EXISTS idx_collection_upload_time ON collection_data(upload_time DESC);
CREATE INDEX IF NOT EXISTS idx_collection_device_id ON collection_data(device_id);

-- 創建 software_data 表
CREATE TABLE IF NOT EXISTS software_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info TEXT,
    ip_location TEXT,
    accounts TEXT,
    collections TEXT,
    invitations TEXT,
    statistics TEXT,
    status VARCHAR(50),
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_software_activation_code ON software_data(activation_code);
CREATE INDEX IF NOT EXISTS idx_software_device_id ON software_data(device_id);
"""
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 執行每個命令
        for command in sql_commands.split(';'):
            command = command.strip()
            if command:
                print(f"執行: {command[:50]}...")
                cur.execute(command)
        
        conn.commit()
        
        # 驗證表已創建
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('collection_data', 'software_data')
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print("\n✅ 成功創建的表：")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 檢查 collection_data 表結構
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'collection_data'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 collection_data 表結構：")
        for col in cur.fetchall():
            print(f"  - {col[0]}: {col[1]}")
        
        cur.close()
        conn.close()
        
        print("\n✅ 所有操作完成！")
        
    except Exception as e:
        print(f"\n❌ 錯誤：{e}")

if __name__ == "__main__":
    execute_sql()