#!/usr/bin/env python3
"""
創建表的簡化版本 - 使用基本 SQL
"""
import os

def create_tables_sql():
    """生成創建表的 SQL 語句"""
    
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

-- 檢查表
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('collection_data', 'software_data')
ORDER BY table_name;
"""
    
    print("=== SQL 語句已生成 ===")
    print("請在 Railway 的 PostgreSQL 控制台執行以下 SQL：")
    print("-" * 60)
    print(sql_commands)
    print("-" * 60)
    
    # 保存到文件
    with open('create_tables.sql', 'w', encoding='utf-8') as f:
        f.write(sql_commands)
    print("\nSQL 已保存到 create_tables.sql")
    
    # 檢查環境
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"\n✓ DATABASE_URL 已設置")
        if 'postgres.railway.internal' in db_url:
            print("  使用內部連接")
        elif 'proxy.rlwy.net' in db_url:
            print("  使用外部連接")
    else:
        print("\n✗ DATABASE_URL 未設置")

if __name__ == "__main__":
    create_tables_sql()