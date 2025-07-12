#!/usr/bin/env python3
"""
修復上傳數據的缺失字段
"""
import psycopg2
import json
from datetime import datetime

# PostgreSQL 連接
DATABASE_URL = "postgresql://postgres:KJuMwmpKTPLNteUICkjMoNslsvwxodHa@interchange.proxy.rlwy.net:12086/railway"

def fix_existing_data():
    """修復現有數據的缺失字段"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 查詢需要修復的記錄
        cur.execute("""
            SELECT id, members_data 
            FROM collection_data 
            WHERE group_name = 'unknown' OR group_name IS NULL
        """)
        
        records = cur.fetchall()
        print(f"找到 {len(records)} 條需要修復的記錄")
        
        for record_id, members_data_str in records:
            try:
                # 解析成員數據
                members_data = json.loads(members_data_str) if members_data_str else []
                
                # 從成員數據中提取群組名稱
                group_name = 'Unknown'
                if members_data and len(members_data) > 0:
                    first_member = members_data[0]
                    group_name = first_member.get('group_name', 'Unknown')
                
                # 更新記錄
                cur.execute("""
                    UPDATE collection_data 
                    SET group_name = %s 
                    WHERE id = %s
                """, (group_name, record_id))
                
                print(f"✓ 修復記錄 {record_id}: {group_name}")
                
            except Exception as e:
                print(f"✗ 修復記錄 {record_id} 失敗: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n修復完成！")
        
    except Exception as e:
        print(f"錯誤: {e}")

def check_data():
    """檢查數據狀態"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 查詢最新的數據
        cur.execute("""
            SELECT 
                id,
                activation_code,
                device_id,
                device_info,
                ip_location,
                group_name,
                members_count,
                upload_time
            FROM collection_data 
            ORDER BY upload_time DESC 
            LIMIT 5
        """)
        
        print("\n最新的5條記錄：")
        print("-" * 120)
        print(f"{'ID':^5} | {'激活碼':^10} | {'設備ID':^16} | {'設備信息':^20} | {'IP位置':^20} | {'群組名稱':^30} | {'成員數':^6}")
        print("-" * 120)
        
        for row in cur.fetchall():
            device_info = json.loads(row[3]) if row[3] else {}
            ip_location = json.loads(row[4]) if row[4] else {}
            
            device_str = f"{device_info.get('platform', 'N/A')}" if device_info else "空"
            ip_str = f"{ip_location.get('city', 'N/A')}" if ip_location else "空"
            
            print(f"{row[0]:^5} | {row[1]:^10} | {row[2]:^16} | {device_str:^20} | {ip_str:^20} | {row[5][:30]:^30} | {row[6]:^6}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    print("=== 修復上傳數據缺失字段 ===")
    
    # 先檢查當前狀態
    print("\n當前數據狀態：")
    check_data()
    
    # 執行修復
    print("\n開始修復...")
    fix_existing_data()
    
    # 再次檢查
    print("\n修復後的數據狀態：")
    check_data()