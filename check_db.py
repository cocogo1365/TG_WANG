#!/usr/bin/env python3
"""檢查數據庫連接"""
import os

print("=== 檢查數據庫 ===")

# 檢查環境變量
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("✗ DATABASE_URL 未設置")
    exit(1)

print("✓ DATABASE_URL 已設置")

# 嘗試連接（不使用psycopg2，因為可能未安裝）
try:
    # 從DATABASE_URL提取信息
    if 'postgresql://' in db_url:
        parts = db_url.replace('postgresql://', '').split('@')
        if len(parts) == 2:
            host_info = parts[1].split(':')[0]
            print(f"  主機: {host_info}")
            print("  數據庫類型: PostgreSQL")
    
    # 嘗試使用內置的database_adapter
    try:
        from database_adapter import DatabaseAdapter
        adapter = DatabaseAdapter()
        print(f"\n=== DatabaseAdapter 狀態 ===")
        print(f"使用PostgreSQL: {adapter.use_postgres}")
        
        # 嘗試獲取激活碼
        codes = adapter.get_activation_codes()
        if codes and 'activation_codes' in codes:
            ac_dict = codes['activation_codes']
            print(f"激活碼總數: {len(ac_dict)}")
            
            if 'SHOW1365' in ac_dict:
                print("\n✓ 找到 SHOW1365 激活碼")
                show_code = ac_dict['SHOW1365']
                print(f"  類型: {show_code.get('plan_type')}")
                print(f"  已使用: {show_code.get('used')}")
                print(f"  設備ID: {show_code.get('used_by_device')}")
            else:
                print("\n✗ 未找到 SHOW1365 激活碼")
    except ImportError:
        print("✗ 無法導入 database_adapter")
    except Exception as e:
        print(f"✗ DatabaseAdapter 錯誤: {e}")
        
except Exception as e:
    print(f"錯誤: {e}")