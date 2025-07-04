#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同時啟動TG機器人和API服務
"""

import os
import subprocess
import threading
import time
import signal
import sys

def start_tg_bot():
    """啟動TG機器人"""
    print("🤖 啟動TG機器人...")
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except Exception as e:
        print(f"❌ TG機器人啟動失敗: {e}")

def start_api_service():
    """啟動API服務"""
    print("🌐 啟動API服務...")
    try:
        import uvicorn
        uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    except Exception as e:
        print(f"❌ API服務啟動失敗: {e}")

def signal_handler(sig, frame):
    """處理終止信號"""
    print("\n👋 正在關閉服務...")
    sys.exit(0)

if __name__ == "__main__":
    # 註冊信號處理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 啟動雙服務模式")
    print("=" * 40)
    
    # 創建線程
    bot_thread = threading.Thread(target=start_tg_bot, daemon=True)
    api_thread = threading.Thread(target=start_api_service, daemon=True)
    
    # 啟動線程
    bot_thread.start()
    time.sleep(2)  # 讓機器人先啟動
    api_thread.start()
    
    print("✅ 兩個服務都已啟動")
    print("🤖 TG機器人正在運行...")
    print("🌐 API服務正在運行...")
    
    try:
        # 保持主線程運行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 服務已停止")
        sys.exit(0)