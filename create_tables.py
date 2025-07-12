#!/usr/bin/env python3
"""
在 Railway PostgreSQL 中創建必要的表
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def create_tables():
    """創建採集數據相關的表"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("錯誤：未設置 DATABASE_URL")
        return False
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 創建 collection_data 表
        print("創建 collection_data 表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS collection_data (
                id SERIAL PRIMARY KEY,
                activation_code VARCHAR(50) NOT NULL,
                device_id VARCHAR(100),
                device_info JSONB,
                ip_location JSONB,
                group_name VARCHAR(255),
                group_link TEXT,
                collection_method VARCHAR(100) DEFAULT '活躍用戶採集',
                members_count INTEGER DEFAULT 0,
                members_data JSONB,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 創建索引
        print("創建索引...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_activation_code ON collection_data(activation_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_upload_time ON collection_data(upload_time DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_device_id ON collection_data(device_id)")
        
        # 創建 software_data 表
        print("創建 software_data 表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS software_data (
                id SERIAL PRIMARY KEY,
                activation_code VARCHAR(50) NOT NULL,
                device_id VARCHAR(100),
                device_info JSONB,
                ip_location JSONB,
                accounts JSONB,
                collections JSONB,
                invitations JSONB,
                statistics JSONB,
                status VARCHAR(50),
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 創建索引
        cur.execute("CREATE INDEX IF NOT EXISTS idx_software_activation_code ON software_data(activation_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_software_device_id ON software_data(device_id)")
        
        conn.commit()
        
        # 檢查表是否創建成功
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('collection_data', 'software_data')
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print("\n已創建的表：")
        for table in tables:
            print(f"  ✓ {table[0]}")
        
        # 檢查 SHOW1365 激活碼
        cur.execute("SELECT * FROM activation_codes WHERE code = %s", ('SHOW1365',))
        show_code = cur.fetchone()
        if show_code:
            print(f"\n✓ 找到 SHOW1365 激活碼")
        else:
            print(f"\n✗ 未找到 SHOW1365 激活碼")
        
        cur.close()
        conn.close()
        
        print("\n✓ 所有表創建成功！")
        return True
        
    except Exception as e:
        print(f"\n✗ 錯誤：{e}")
        return False

if __name__ == "__main__":
    print("=== 創建 PostgreSQL 表 ===")
    create_tables()