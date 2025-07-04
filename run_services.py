#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在Railway上同時運行API和TG機器人
"""

import os
import sys
import asyncio
import threading
import logging
from concurrent.futures import ThreadPoolExecutor

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_api():
    """運行API服務"""
    logger.info("🌐 啟動API服務...")
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

def run_bot():
    """運行TG機器人"""
    logger.info("🤖 啟動TG機器人...")
    # 導入並運行main.py
    import main

def main():
    """主函數"""
    logger.info("🚀 Railway雙服務啟動器")
    logger.info("=" * 50)
    
    # 檢查環境變量
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN未設置！")
        sys.exit(1)
    
    logger.info("✅ 環境變量已加載")
    
    # 使用線程池同時運行兩個服務
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交任務
        api_future = executor.submit(run_api)
        bot_future = executor.submit(run_bot)
        
        logger.info("✅ 兩個服務已啟動")
        
        try:
            # 等待任務完成（永遠不會完成，除非出錯）
            api_future.result()
            bot_future.result()
        except KeyboardInterrupt:
            logger.info("👋 收到停止信號")
        except Exception as e:
            logger.error(f"❌ 服務出錯: {e}")

if __name__ == "__main__":
    main()