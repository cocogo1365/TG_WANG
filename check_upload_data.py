#!/usr/bin/env python3
"""
檢查採集數據上傳狀態
"""

import os
import json
import psycopg2
from datetime import datetime
from database_adapter import DatabaseAdapter

def check_file_uploads():
    """檢查文件系統中的上傳數據"""
    print("=" * 60)
    print("檢查文件系統上傳數據")
    print("=" * 60)
    
    upload_dir = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
    
    if not os.path.exists(upload_dir):
        print(f"❌ 上傳目錄不存在: {upload_dir}")
        return
    
    files = [f for f in os.listdir(upload_dir) if f.endswith('.json')]
    print(f"✅ 找到 {len(files)} 個上傳文件")
    
    for file in files[-5:]:  # 顯示最新5個
        filepath = os.path.join(upload_dir, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"\n📄 文件: {file}")
            print(f"   激活碼: {data.get('activation_code')}")
            print(f"   設備ID: {data.get('device_id')}")
            print(f"   上傳時間: {data.get('upload_time')}")
            
            # 檢查collections
            collections = data.get('collections', [])
            if collections:
                print(f"   採集數據: {len(collections)} 組")
                for col in collections:
                    print(f"     - {col.get('group_name', 'Unknown')}: {col.get('members_count', 0)} 個成員")
            
            # 檢查舊格式
            if 'collection_info' in data:
                info = data['collection_info']
                print(f"   採集方法: {info.get('collection_method')}")
                print(f"   目標群組: {info.get('target_groups')}")
        
        except Exception as e:
            print(f"   ❌ 讀取錯誤: {e}")

def check_postgresql():
    """檢查PostgreSQL中的數據"""
    print("\n" + "=" * 60)
    print("檢查PostgreSQL數據庫")
    print("=" * 60)
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ 未設置DATABASE_URL環境變量")
        return
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 檢查表是否存在
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('collection_data', 'software_data')
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        if 'collection_data' in tables:
            print("✅ collection_data 表存在")
            cur.execute("SELECT COUNT(*) FROM collection_data")
            count = cur.fetchone()[0]
            print(f"   記錄數: {count}")
            
            if count > 0:
                cur.execute("""
                    SELECT activation_code, group_name, members_count, upload_time 
                    FROM collection_data 
                    ORDER BY upload_time DESC 
                    LIMIT 5
                """)
                print("\n   最新記錄:")
                for row in cur.fetchall():
                    print(f"     {row[0]} | {row[1]} | {row[2]}成員 | {row[3]}")
        else:
            print("❌ collection_data 表不存在")
        
        if 'software_data' in tables:
            print("\n✅ software_data 表存在")
            cur.execute("SELECT COUNT(*) FROM software_data")
            count = cur.fetchone()[0]
            print(f"   記錄數: {count}")
        else:
            print("\n❌ software_data 表不存在")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ PostgreSQL連接錯誤: {e}")

def check_with_adapter():
    """使用DatabaseAdapter檢查"""
    print("\n" + "=" * 60)
    print("使用DatabaseAdapter檢查")
    print("=" * 60)
    
    try:
        adapter = DatabaseAdapter()
        print(f"✅ 使用{'PostgreSQL' if adapter.use_postgres else 'JSON文件'}")
        
        # 檢查激活碼
        codes = adapter.get_activation_codes()
        if codes and 'activation_codes' in codes:
            ac_dict = codes['activation_codes']
            print(f"\n找到 {len(ac_dict)} 個激活碼")
            
            # 檢查SHOW1365
            if 'SHOW1365' in ac_dict:
                show_code = ac_dict['SHOW1365']
                print(f"\n✅ SHOW1365 激活碼:")
                print(f"   類型: {show_code.get('plan_type')}")
                print(f"   使用: {show_code.get('used')}")
                print(f"   設備: {show_code.get('used_by_device')}")
            else:
                print("\n❌ 未找到SHOW1365激活碼")
                
    except Exception as e:
        print(f"❌ DatabaseAdapter錯誤: {e}")

def test_api_upload():
    """測試API上傳"""
    print("\n" + "=" * 60)
    print("測試數據上傳API")
    print("=" * 60)
    
    test_data = {
        'activation_code': 'SHOW1365',
        'device_id': 'test_device_001',
        'device_info': {
            'hostname': 'TestPC',
            'platform': 'Windows Test'
        },
        'ip_location': {
            'city': 'Test City',
            'country': 'Test Country'
        },
        'group_info': {
            'name': '測試群組',
            'link': 'https://t.me/test'
        },
        'members': [
            {'id': 1, 'username': 'test1', 'first_name': '測試1'},
            {'id': 2, 'username': 'test2', 'first_name': '測試2'}
        ]
    }
    
    print("測試數據準備完成")
    print(f"激活碼: {test_data['activation_code']}")
    print(f"成員數: {len(test_data['members'])}")
    
    # 如果在Railway環境，可以直接調用API
    # import requests
    # response = requests.post('http://localhost:8080/api/upload_collection_data', json=test_data)
    # print(f"API響應: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("採集數據上傳診斷工具")
    print("=" * 60)
    print(f"當前時間: {datetime.now()}")
    print(f"工作目錄: {os.getcwd()}")
    print(f"DATABASE_URL: {'已設置' if os.environ.get('DATABASE_URL') else '未設置'}")
    print(f"UPLOAD_DATA_DIR: {os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')}")
    
    check_file_uploads()
    check_postgresql()
    check_with_adapter()
    # test_api_upload()  # 可選：測試上傳
    
    print("\n診斷完成！")