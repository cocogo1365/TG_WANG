#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速啟動TG機器人 - 用於測試免費試用功能
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """加載.env文件中的環境變量"""
    env_file = Path('.env')
    if env_file.exists():
        print("📁 找到.env配置文件，正在加載...")
        
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if not value.startswith('your_') and value != 'here':
                        os.environ[key] = value
                        print(f"✅ 設置 {key}")
                    else:
                        print(f"⚠️ 需要配置 {key}")
    else:
        print("❌ 未找到.env文件")

def check_config():
    """檢查必要配置"""
    required_vars = ['BOT_TOKEN', 'TEST_MODE']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing.append(var)
    
    return missing

def main():
    """主函數"""
    print("🚀 TG機器人快速啟動工具")
    print("=" * 50)
    
    # 設置測試模式的基本配置
    os.environ['TEST_MODE'] = 'true'
    os.environ['USDT_ADDRESS'] = 'TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP'
    os.environ['USDT_CONTRACT'] = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
    
    # 如果沒有BOT_TOKEN，創建測試Token
    if not os.getenv('BOT_TOKEN'):
        print("⚠️ 未設置BOT_TOKEN")
        print("📝 請按以下步驟獲取Bot Token:")
        print("1. 在Telegram中搜索 @BotFather")
        print("2. 發送 /newbot 創建新機器人")
        print("3. 選擇機器人名稱和用戶名")
        print("4. 獲取Token並輸入:")
        
        bot_token = input("\n請輸入您的Bot Token: ").strip()
        if bot_token:
            os.environ['BOT_TOKEN'] = bot_token
            print("✅ Bot Token已設置")
        else:
            print("❌ 未設置Bot Token，無法啟動")
            return False
    
    # 設置管理員ID
    if not os.getenv('ADMIN_IDS'):
        print("\n📝 請輸入您的Telegram用戶ID:")
        print("(可以通過 @userinfobot 獲取您的用戶ID)")
        
        user_id = input("請輸入您的用戶ID: ").strip()
        if user_id and user_id.isdigit():
            os.environ['ADMIN_IDS'] = user_id
            print("✅ 管理員ID已設置")
        else:
            print("⚠️ 未設置管理員ID，將使用默認值")
            os.environ['ADMIN_IDS'] = '123456789'
    
    print("\n🔧 當前配置:")
    print(f"BOT_TOKEN: {'已設置' if os.getenv('BOT_TOKEN') else '未設置'}")
    print(f"TEST_MODE: {os.getenv('TEST_MODE')}")
    print(f"ADMIN_IDS: {os.getenv('ADMIN_IDS')}")
    print(f"USDT_ADDRESS: {os.getenv('USDT_ADDRESS')}")
    
    # 檢查配置
    missing = check_config()
    if missing:
        print(f"\n❌ 仍有缺少的配置: {', '.join(missing)}")
        print("無法啟動機器人")
        return False
    
    print("\n✅ 配置檢查通過!")
    print("🚀 正在啟動TG機器人...")
    
    try:
        # 導入並啟動機器人
        import main
        print("✅ 機器人啟動成功!")
        print("💡 現在可以在Telegram中測試免費試用功能了")
        
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 用戶手動停止")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        input("按回車鍵退出...")