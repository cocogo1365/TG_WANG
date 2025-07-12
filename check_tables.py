#!/usr/bin/env python3
"""
檢查表是否存在
"""
import os

db_url = os.environ.get('DATABASE_URL')
if db_url:
    print("✓ DATABASE_URL 已設置")
    
    # 嘗試使用 database_adapter
    try:
        from database_adapter import DatabaseAdapter
        adapter = DatabaseAdapter()
        
        if adapter.use_postgres:
            print("✓ 使用 PostgreSQL")
            
            # 測試連接
            import psycopg2
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # 列出所有表
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = cur.fetchall()
            print(f"\n找到 {len(tables)} 個表：")
            for table in tables:
                print(f"  - {table[0]}")
            
            # 檢查 collection_data
            if 'collection_data' in [t[0] for t in tables]:
                cur.execute("SELECT COUNT(*) FROM collection_data")
                count = cur.fetchone()[0]
                print(f"\n✓ collection_data 表存在，有 {count} 條記錄")
            else:
                print("\n✗ collection_data 表不存在")
            
            cur.close()
            conn.close()
        else:
            print("✗ DatabaseAdapter 使用 JSON 文件模式")
    except Exception as e:
        print(f"✗ 錯誤：{e}")
else:
    print("✗ DATABASE_URL 未設置")