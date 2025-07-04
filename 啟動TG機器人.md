# 🤖 啟動TG機器人

由於Railway可能只運行一個進程，我們有幾個選擇：

## 選項1：本地運行TG機器人

在您的電腦上運行機器人：

```powershell
cd C:\Users\XX11\Documents\GitHub\TG_WANG

# 設置環境變量
$env:BOT_TOKEN="7723514301:AAEya9QRLcAPgmPrTKC5BkAtYWAo8nvKvos"
$env:ADMIN_IDS="7537903238"
$env:TEST_MODE="true"
$env:TRONGRID_API_KEY="26af1138-bb1c-446d-81df-b25e957e44db"
$env:USDT_ADDRESS="TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP"
$env:USDT_CONTRACT="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# 運行機器人
python main.py
```

## 選項2：使用其他免費服務運行機器人

1. **Replit** - 免費運行Python機器人
2. **Heroku** - 免費dyno
3. **PythonAnywhere** - 免費Python托管

## 選項3：在Railway創建第二個服務

1. 創建新的Railway服務專門運行機器人
2. 連接同一個GitHub倉庫
3. 使用不同的Procfile

## 選項4：修改為單一服務

將API整合到機器人中，讓機器人同時處理：
- Telegram命令
- HTTP API請求