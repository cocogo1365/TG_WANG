#!/usr/bin/env python3
"""
清理重疊文件腳本
移除功能重複的文件，保留主要版本
"""

import os
import shutil
from datetime import datetime

# 要刪除的重疊文件列表
DUPLICATE_FILES = [
    # 備份和舊版本
    "app_backup.py",
    "bot_database.json.backup_20250711_210558",
    
    # 重複的API服務
    "app_with_data_api.py",  # 保留 app.py
    "簡化雲端API.py",  # 保留 app.py
    "雲端API服務.py",  # 保留 app.py
    
    # 重複的啟動腳本
    "run_both.py",  # 保留 integrated_enterprise_app.py
    "start_both.py",  # 保留 integrated_enterprise_app.py
    "run_services.py",  # 保留 integrated_enterprise_app.py
    
    # 重複的測試文件
    "test_simple_api.py",  # 保留 test_api.py
    "simple_debug.py",  # 保留 full_diagnosis.py
    "manual_test.py",  # 保留 test_api.py
    
    # 重複的修復腳本
    "fix_software_uploader.py",  # 功能已整合
    "fix_upload_data_fields.py",  # 功能已整合
    "fix_upload_to_postgresql.py",  # 功能已整合
    "quick_fix_upload.py",  # 功能已整合
    "quick_fix_upload_timer.py",  # 功能已整合
    
    # 重複的部署文件
    "Procfile.api",  # 保留 Procfile.integrated
    "Procfile.bot",  # 保留 Procfile.integrated
    "Procfile.data",  # 保留 Procfile.integrated
    "Procfile.web",  # 保留 Procfile.integrated
    
    # 臨時和測試文件
    "deploy_commands.txt",
    "railway_deploy.txt",
    "setup.txt",
    "env_example.txt",
    "DEPLOY_TRIGGER.txt",
    
    # 中文命名的重複文件
    "快速啟動機器人.py",  # 功能已在 main.py
    "啟用雲端同步.py",  # 功能已整合
    "整合雲端同步.py",  # 功能已整合
    "測試雲端同步.py",  # 功能已整合
    "激活碼系統增強.py",  # 功能已整合
    "雲端同步機器人.py",  # 功能已整合
    "添加新激活碼.py",  # 功能已整合
]

# 要保留的主要文件
MAIN_FILES = {
    "API服務": "app.py",
    "Telegram機器人": "main.py",
    "整合應用": "integrated_enterprise_app.py",
    "企業網站": "enterprise_web_app.py",
    "多機器人管理": "multi_bot_enterprise_app.py",
    "數據庫": "database.py",
    "配置": "config.py",
    "激活碼管理": "activation_codes.py",
    "TRON監控": "tron_monitor.py",
}

def backup_file(filepath):
    """備份文件到 backup 目錄"""
    backup_dir = "backup_duplicates"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    filename = os.path.basename(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
    
    try:
        shutil.copy2(filepath, backup_path)
        print(f"✓ 備份: {filename} -> {backup_path}")
        return True
    except Exception as e:
        print(f"✗ 備份失敗 {filename}: {e}")
        return False

def cleanup_duplicates():
    """清理重複文件"""
    print("開始清理重複文件...")
    print("=" * 50)
    
    removed_count = 0
    failed_count = 0
    
    for filename in DUPLICATE_FILES:
        filepath = filename
        
        if os.path.exists(filepath):
            print(f"\n處理: {filename}")
            
            # 先備份
            if backup_file(filepath):
                # 然後刪除
                try:
                    os.remove(filepath)
                    print(f"✓ 已刪除: {filename}")
                    removed_count += 1
                except Exception as e:
                    print(f"✗ 刪除失敗: {filename} - {e}")
                    failed_count += 1
            else:
                failed_count += 1
        else:
            print(f"⚠ 文件不存在: {filename}")
    
    print("\n" + "=" * 50)
    print(f"清理完成！")
    print(f"✓ 成功刪除: {removed_count} 個文件")
    print(f"✗ 失敗: {failed_count} 個文件")
    
    print("\n保留的主要文件:")
    for purpose, filename in MAIN_FILES.items():
        if os.path.exists(filename):
            print(f"✓ {purpose}: {filename}")
        else:
            print(f"⚠ {purpose}: {filename} (不存在)")

def create_file_structure():
    """創建建議的目錄結構"""
    directories = [
        "src",  # 源代碼
        "config",  # 配置文件
        "tests",  # 測試文件
        "docs",  # 文檔
        "scripts",  # 腳本
        "backup_duplicates",  # 備份目錄
    ]
    
    print("\n創建目錄結構:")
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ 創建目錄: {directory}")
        else:
            print(f"⚠ 目錄已存在: {directory}")

if __name__ == "__main__":
    print("TG_WANG 專案文件清理工具")
    print("此腳本將備份並刪除重複的文件")
    print("\n" + "=" * 50)
    
    response = input("\n確定要繼續嗎？(y/n): ")
    if response.lower() == 'y':
        cleanup_duplicates()
        
        print("\n是否要創建建議的目錄結構？(y/n): ")
        response = input()
        if response.lower() == 'y':
            create_file_structure()
    else:
        print("已取消操作")