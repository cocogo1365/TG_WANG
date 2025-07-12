#!/usr/bin/env python3
"""
通過 Railway 環境檢查 PostgreSQL
"""
import os

# 檢查是否在 Railway 環境中
if os.environ.get('RAILWAY_ENVIRONMENT'):
    print("✓ 在 Railway 環境中運行")
else:
    print("⚠️ 不在 Railway 環境中，使用 railway run 執行此腳本")

# 檢查數據庫連接
db_url = os.environ.get('DATABASE_URL')
if db_url:
    print(f"✓ DATABASE_URL 已設置")
    
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 檢查 collection_data 表
        cur.execute("SELECT COUNT(*) FROM collection_data")
        count = cur.fetchone()[0]
        print(f"\n📊 collection_data 表中有 {count} 條記錄")
        
        if count > 0:
            # 查看最新記錄
            cur.execute("""
                SELECT activation_code, group_name, members_count, upload_time 
                FROM collection_data 
                ORDER BY upload_time DESC 
                LIMIT 3
            """)
            
            print("\n最新記錄：")
            for row in cur.fetchall():
                print(f"  {row[0]} | {row[1]} | {row[2]}成員 | {row[3]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 數據庫錯誤: {e}")
else:
    print("❌ DATABASE_URL 未設置")