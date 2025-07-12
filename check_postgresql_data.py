#!/usr/bin/env python3
"""
檢查 PostgreSQL 中的採集數據
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def check_data():
    # 你的 Railway PostgreSQL 連接資訊
    DATABASE_URL = "postgresql://postgres:KJuMwmpKTPLNteUICkjMoNslsvwxodHa@interchange.proxy.rlwy.net:12086/railway"
    
    try:
        print("連接到 PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'collection_data'
            )
        """)
        
        if not cur.fetchone()['exists']:
            print("❌ collection_data 表不存在！")
            return
            
        print("✅ collection_data 表存在")
        
        # 查詢數據總數
        cur.execute("SELECT COUNT(*) as count FROM collection_data")
        total = cur.fetchone()['count']
        print(f"\n📊 總記錄數: {total}")
        
        if total > 0:
            # 查詢最新的5條記錄
            cur.execute("""
                SELECT 
                    id,
                    activation_code,
                    device_id,
                    group_name,
                    members_count,
                    upload_time
                FROM collection_data 
                ORDER BY upload_time DESC 
                LIMIT 5
            """)
            
            records = cur.fetchall()
            print("\n📋 最新的5條記錄:")
            for record in records:
                print(f"\n  ID: {record['id']}")
                print(f"  激活碼: {record['activation_code']}")
                print(f"  設備: {record['device_id']}")
                print(f"  群組: {record['group_name']}")
                print(f"  成員數: {record['members_count']}")
                print(f"  上傳時間: {record['upload_time']}")
                
            # 統計各激活碼的記錄數
            cur.execute("""
                SELECT 
                    activation_code, 
                    COUNT(*) as count,
                    SUM(members_count) as total_members
                FROM collection_data 
                GROUP BY activation_code
                ORDER BY count DESC
            """)
            
            stats = cur.fetchall()
            print("\n📈 激活碼統計:")
            for stat in stats:
                print(f"  {stat['activation_code']}: {stat['count']} 條記錄, 共 {stat['total_members']} 個成員")
                
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    print("=== 檢查 PostgreSQL 採集數據 ===")
    print(f"時間: {datetime.now()}\n")
    check_data()