#!/usr/bin/env python3
"""簡單的上傳數據檢查"""
import os
import json
import glob

print("=== 檢查上傳目錄 ===")
upload_dir = 'uploaded_data'

if os.path.exists(upload_dir):
    print(f"✓ 目錄存在: {upload_dir}")
    all_files = os.listdir(upload_dir)
    json_files = [f for f in all_files if f.endswith('.json')]
    print(f"  總文件數: {len(all_files)}")
    print(f"  JSON文件數: {len(json_files)}")
    
    # 查找SHOW1365相關文件
    show_files = [f for f in json_files if 'SHOW1365' in f]
    print(f"\n=== SHOW1365 相關文件 ===")
    print(f"找到 {len(show_files)} 個文件")
    
    for f in show_files[:5]:
        filepath = os.path.join(upload_dir, f)
        size = os.path.getsize(filepath)
        print(f"  - {f} ({size} bytes)")
        
    # 顯示最新的3個文件
    print(f"\n=== 最新上傳文件 ===")
    json_files_sorted = sorted(json_files, reverse=True)[:3]
    for f in json_files_sorted:
        print(f"  - {f}")
        
else:
    print(f"✗ 目錄不存在: {upload_dir}")
    print("  嘗試創建目錄...")
    try:
        os.makedirs(upload_dir)
        print("  ✓ 目錄創建成功")
    except Exception as e:
        print(f"  ✗ 創建失敗: {e}")

print("\n=== 檢查環境變量 ===")
print(f"DATABASE_URL: {'已設置' if os.environ.get('DATABASE_URL') else '未設置'}")
print(f"UPLOAD_DATA_DIR: {os.environ.get('UPLOAD_DATA_DIR', '未設置，使用默認值')}")