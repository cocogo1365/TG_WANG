@echo off
echo 🚄 Railway部署腳本
echo ==================

echo 📍 進入項目目錄...
cd /d "C:\Users\XX11\Documents\GitHub\TG_WANG"

echo 🚀 開始部署到Railway...
railway up

echo ⚙️ 設置環境變量...
railway variables set API_KEY=tg-api-secure-key-2024
railway variables set DB_PATH=bot_database.json
railway variables set ADMIN_IDS=7537903238
railway variables set BOT_TOKEN=7723514301:AAEya9QRLcAPgmPrTKC5BkAtYWAo8nvKvos
railway variables set TEST_MODE=true
railway variables set TRONGRID_API_KEY=26af1138-bb1c-446d-81df-b25e957e44db
railway variables set USDT_ADDRESS=TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP
railway variables set USDT_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

echo 🌐 獲取域名...
railway domain

echo ✅ 部署完成！
echo 📋 查看狀態：railway status
echo 📋 查看日誌：railway logs
pause