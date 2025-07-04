#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同時運行API和TG機器人 - Railway版本
"""

import os
import sys
import asyncio
import subprocess
import signal
import logging
from multiprocessing import Process

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_api():
    """運行API服務"""
    try:
        logger.info("🌐 正在啟動API服務...")
        port = int(os.getenv("PORT", 8000))
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", str(port)
        ])
    except Exception as e:
        logger.error(f"❌ API服務啟動失敗: {e}")

def run_bot():
    """運行TG機器人"""
    try:
        logger.info("🤖 正在啟動TG機器人...")
        # 直接運行main.py
        subprocess.run([sys.executable, "main.py"])
    except Exception as e:
        logger.error(f"❌ TG機器人啟動失敗: {e}")

def signal_handler(signum, frame):
    """處理停止信號"""
    logger.info("👋 收到停止信號，正在關閉服務...")
    sys.exit(0)

def main():
    """主函數"""
    # 註冊信號處理
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Railway雙服務啟動器")
    logger.info("=" * 50)
    
    # 檢查關鍵環境變量
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN未設置！")
        sys.exit(1)
    
    logger.info(f"✅ BOT_TOKEN已設置: {bot_token[:20]}...")
    logger.info(f"✅ API_KEY已設置: {os.getenv('API_KEY', 'Not set')}")
    logger.info(f"✅ TEST_MODE: {os.getenv('TEST_MODE', 'Not set')}")
    
    # 創建進程
    api_process = Process(target=run_api, daemon=True)
    bot_process = Process(target=run_bot)
    
    try:
        # 啟動API進程
        api_process.start()
        logger.info("✅ API進程已啟動")
        
        # 啟動機器人進程（主進程）
        logger.info("✅ 正在啟動機器人進程...")
        bot_process.start()
        
        # 等待進程
        bot_process.join()
        
    except KeyboardInterrupt:
        logger.info("👋 收到中斷信號")
    except Exception as e:
        logger.error(f"❌ 服務出錯: {e}")
    finally:
        # 終止進程
        if api_process.is_alive():
            api_process.terminate()
        if bot_process.is_alive():
            bot_process.terminate()
        logger.info("👋 服務已停止")

if __name__ == "__main__":
    main()