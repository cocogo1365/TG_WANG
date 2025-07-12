#!/usr/bin/env python3
"""
TG旺企業管理系統 - 整合TG機器人數據版
串聯機器人數據，顯示真實的訂單、激活碼、用戶數據
更新：2025/07/12 - 支持 PostgreSQL 存儲採集數據
"""

import os
import json
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from database_adapter import DatabaseAdapter

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 初始化數據庫適配器
db_adapter = DatabaseAdapter()

# 配置
BOT_DATABASE_PATH = os.environ.get('BOT_DATABASE_PATH', 'bot_database.json')
UPLOAD_DATA_DIR = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'tgwang2024')
MANAGER_PASSWORD = os.environ.get('MANAGER_PASSWORD', 'manager123')
AGENT_PASSWORD = os.environ.get('AGENT_PASSWORD', 'agent123')

# 管理員帳號
ADMIN_USERS = {
    "admin": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
    "manager": hashlib.sha256(MANAGER_PASSWORD.encode()).hexdigest(),
    "agent": hashlib.sha256(AGENT_PASSWORD.encode()).hexdigest()
}

# 權限配置
USER_ROLES = {
    "admin": {"name": "超級管理員", "permissions": ["all"]},
    "manager": {"name": "業務經理", "permissions": ["revenue", "customers", "users"]},
    "agent": {"name": "代理商", "permissions": ["revenue_own", "customers_own"]}
}

def get_bot_database():
    """獲取機器人數據庫"""
    try:
        # 優先使用數據庫適配器
        db_data = db_adapter.get_activation_codes()
        
        # 如果有PostgreSQL數據，使用它
        if db_data and db_data.get("activation_codes"):
            # 補充其他必要字段
            if os.path.exists(BOT_DATABASE_PATH):
                with open(BOT_DATABASE_PATH, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    # 合併數據：激活碼使用PostgreSQL，其他使用本地
                    local_data["activation_codes"] = db_data["activation_codes"]
                    return local_data
            else:
                return {
                    "users": {},
                    "orders": {},
                    "activation_codes": db_data["activation_codes"],
                    "trial_users": [],
                    "transactions": {},
                    "statistics": {
                        "total_revenue": 0,
                        "orders_created": 0,
                        "activations_generated": 0
                    }
                }
        
        # 降級到本地JSON文件
        if os.path.exists(BOT_DATABASE_PATH):
            with open(BOT_DATABASE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "users": {},
                "orders": {},
                "activation_codes": {},
                "trial_users": [],
                "transactions": {},
                "statistics": {
                    "total_revenue": 0,
                    "orders_created": 0,
                    "activations_generated": 0
                }
            }
    except Exception as e:
        print(f"讀取機器人數據庫失敗: {e}")
        return {
            "users": {},
            "orders": {},
            "activation_codes": {},
            "trial_users": [],
            "transactions": {},
            "statistics": {
                "total_revenue": 0,
                "orders_created": 0,
                "activations_generated": 0
            }
        }

def get_collection_data_from_postgresql():
    """從 PostgreSQL 獲取採集數據"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return []
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import json as json_lib
        
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'collection_data'
            )
        """)
        if not cur.fetchone()['exists']:
            cur.close()
            conn.close()
            return []
        
        # 獲取最新的100條記錄
        cur.execute("""
            SELECT * FROM collection_data 
            ORDER BY upload_time DESC 
            LIMIT 100
        """)
        
        rows = cur.fetchall()
        result = []
        
        for row in rows:
            # 轉換為兼容的格式
            record = {
                'activation_code': row['activation_code'],
                'device_id': row['device_id'],
                'device_info': json_lib.loads(row['device_info']) if row['device_info'] else {},
                'ip_location': json_lib.loads(row['ip_location']) if row['ip_location'] else {},
                'upload_time': row['upload_time'].isoformat() if row['upload_time'] else '',
                'collections': [{
                    'group_name': row['group_name'],
                    'group_link': row['group_link'],
                    'method': row['collection_method'],
                    'members_count': row['members_count'],
                    'members': json_lib.loads(row['members_data']) if row['members_data'] else [],
                    'timestamp': row['upload_time'].isoformat() if row['upload_time'] else ''
                }]
            }
            result.append(record)
        
        cur.close()
        conn.close()
        
        logger.info(f"從 PostgreSQL 讀取了 {len(result)} 條採集記錄")
        return result
        
    except Exception as e:
        logger.error(f"從 PostgreSQL 讀取數據失敗: {e}")
        return []

def get_uploaded_data():
    """獲取上傳的採集數據（優先從PostgreSQL，降級到文件系統）"""
    uploaded_data = []
    
    # 首先嘗試從 PostgreSQL 獲取
    pg_data = get_collection_data_from_postgresql()
    if pg_data:
        uploaded_data.extend(pg_data)
        logger.info(f"從 PostgreSQL 獲取了 {len(pg_data)} 條數據")
    
    # 然後從文件系統獲取（避免重複）
    existing_codes = {data['activation_code'] for data in uploaded_data}
    
    try:
        if os.path.exists(UPLOAD_DATA_DIR):
            for filename in os.listdir(UPLOAD_DATA_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(UPLOAD_DATA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # 避免重複
                            if data.get('activation_code') not in existing_codes:
                                uploaded_data.append(data)
                    except Exception as e:
                        logger.error(f"讀取文件失敗 {filename}: {e}")
    except Exception as e:
        logger.error(f"讀取上傳目錄失敗: {e}")
    
    logger.info(f"總共獲取了 {len(uploaded_data)} 條採集數據")
    return uploaded_data

def get_plan_type_chinese(plan_type):
    """轉換方案類型為中文"""
    plan_mapping = {
        'trial': '試用版',
        'weekly': '週方案',
        'monthly': '月方案',
        'quarterly': '季方案',
        'yearly': '年方案',
        'premium': '高級版',
        'enterprise': '企業版'
    }
    return plan_mapping.get(plan_type, plan_type)

def format_currency(amount, currency='TRX'):
    """格式化貨幣顯示"""
    if currency == 'TRX':
        return f"{amount:.2f} TRX"
    elif currency == 'USDT':
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"

# HTML模板
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TG-WANG 登入</title>
  <!-- 載入字體與FontAwesome圖示 -->
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
  <style>
    /* 頁面主背景，使用暗色並置中 */
    body {
      background: #18181b;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
    }
    /* 登入區塊主體：霓虹科技感+陰影+圓角 */
    .neon-box {
      position: relative;
      background: #23232a;
      border-radius: 22px;
      box-shadow: 0 0 44px #09092b, 0 4px 40px #0ef6f6;
      padding: 38px 30px 20px 30px;
      width: 370px;
      color: #fff;
      overflow: hidden;
      z-index: 1;
    }
    /* 外層霓虹光暈動畫框 */
    .neon-box::before, .neon-box::after {
      content: "";
      position: absolute;
      border-radius: 22px;
      z-index: 0;
      pointer-events: none;
    }
    /* 外部動態霓虹邊框 */
    .neon-box::before {
      inset: 0;
      border: 2px solid;
      border-color: #0ff6f6 #fe41a3 #0ff6f6 #fe41a3;
      filter: blur(3px);
      opacity: 0.8;
      animation: borderGlow 3s linear infinite;
    }
    /* 內部暗色裝飾邊框 */
    .neon-box::after {
      inset: 7px;
      border: 1.5px solid #333;
    }
    /* 邊框光暈動畫 */
    @keyframes borderGlow {
      0%   { filter: blur(3px) brightness(1.2);}
      50%  { filter: blur(7px) brightness(1.5);}
      100% { filter: blur(3px) brightness(1.2);}
    }
    /* LOGO字與icon，中央、亮色光暈、彈跳心跳動畫 */
    .neon-logo {
      font-size: 2.1em;
      font-weight: 800;
      letter-spacing: 4px;
      margin-bottom: 14px;
      text-align: center;
      position: relative;
      z-index: 2;
      color: #0ff6f6;
      text-shadow: 0 0 16px #0ff6f6, 0 0 40px #fe41a3;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    .neon-logo .beat {
      color: #fe41a3;
      animation: beat 1s infinite;
      font-size: 1.1em;
      margin-left: 2px;
    }
    /* 心跳動畫效果 */
    @keyframes beat {
      0%, 100% { transform: scale(1);}
      25% { transform: scale(1.25);}
      50% { transform: scale(1);}
    }
    /* 標題文字樣式 */
    .neon-title {
      text-align: center;
      font-size: 1.16em;
      color: #fff;
      margin-bottom: 18px;
      opacity: .82;
      z-index: 2;
      letter-spacing: 1px;
    }
    /* 輸入框，暗底，圓角，霓虹聚焦 */
    .neon-input {
      background: #242436;
      border: 1.5px solid #36364b;
      outline: none;
      border-radius: 14px;
      padding: 12px 18px;
      color: #fff;
      width: 100%;
      margin-bottom: 18px;
      font-size: 1em;
      transition: border 0.3s, box-shadow 0.3s;
      z-index: 2;
      position: relative;
      box-sizing: border-box;
    }
    .neon-input::placeholder {
      color: #999;
    }
    .neon-input:focus {
      border: 1.5px solid #0ff6f6;
      box-shadow: 0 0 10px #0ff6f699;
    }
    /* 霓虹按鈕樣式，漸層+hover效果 */
    .neon-btn {
      width: 100%;
      padding: 12px 0;
      border-radius: 12px;
      border: none;
      background: linear-gradient(90deg, #08f7fe 0%, #fe41a3 100%);
      color: #fff;
      font-weight: 700;
      font-size: 1.12em;
      letter-spacing: 1px;
      margin-bottom: 12px;
      box-shadow: 0 2px 14px #08f7fe44;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.3s;
      z-index: 2;
      position: relative;
    }
    .neon-btn:hover {
      transform: scale(1.04);
      box-shadow: 0 6px 22px #fe41a355, 0 0 14px #08f7fe77;
    }
    /* 錯誤訊息區塊 */
    .neon-alert {
      background: rgba(254, 65, 163, 0.15);
      border: 1px solid #fe41a3;
      color: #fff;
      border-radius: 8px;
      padding: 10px 15px;
      font-size: 0.97em;
      margin-bottom: 15px;
      text-align: center;
      z-index: 2;
      position: relative;
      box-shadow: 0 0 8px #fe41a388;
    }
    /* 測試帳號小提醒區 */
    .neon-testinfo {
      color: #bbb;
      font-size: 0.97em;
      background: rgba(0,0,0,0.12);
      border-radius: 8px;
      padding: 8px 8px 6px 8px;
      margin-top: 10px;
      text-align: center;
      z-index: 2;
      position: relative;
    }
    /* 響應式，手機適配 */
    @media (max-width: 450px) {
      .neon-box { width: 97vw; min-width: unset; }
      .neon-logo { font-size: 1.2em;}
    }
  </style>
</head>
<body>
  <!-- 登入表單，POST至後端 -->
  <form class="neon-box" method="POST" autocomplete="on">
    <!-- LOGO行，科技感ICON + TG-WANG 字母LOGO + 心跳icon動畫 -->
    <div class="neon-logo">
      <i class="fa-solid fa-robot"></i>
      TG‑WANG
      <i class="fa-solid fa-heartbeat beat"></i>
    </div>
    <div class="neon-title">企業用自動化登入入口</div>
    <!-- 帳號輸入框，支援自動補全 -->
    <input class="neon-input" type="text" name="username" placeholder="帳號 (Username)" required autocomplete="username">
    <!-- 密碼輸入框，支援自動補全 -->
    <input class="neon-input" type="password" name="password" placeholder="密碼 (Password)" required autocomplete="current-password">
    <!-- 登入按鈕 -->
    <button type="submit" class="neon-btn">登入</button>
    <!-- 錯誤訊息顯示區 -->
    {% if error %}
    <div class="neon-alert">
      <i class="fa-solid fa-circle-exclamation"></i> {{ error }}
    </div>
    {% endif %}
    <!-- 測試帳號資訊 -->
    <div class="neon-testinfo">
      <strong>測試帳號：</strong><br>
      admin / tgwang2024（管理員）<br>
      agent / agent123（代理商）
    </div>
  </form>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TG旺企業管理系統 - 機器人數據整合</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            background: #f8f9fa; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sidebar {
            background: white;
            min-height: calc(100vh - 70px);
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            position: fixed;
            width: 250px;
            z-index: 1000;
        }
        .main-content {
            margin-left: 250px;
            padding: 20px;
        }
        .nav-link {
            color: #495057;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 2px 8px;
            transition: all 0.3s;
        }
        .nav-link:hover, .nav-link.active {
            background: #667eea;
            color: white;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.3s;
            border-left: 4px solid #667eea;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9rem;
        }
        .data-table {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .table th {
            background: #f8f9fa;
            font-weight: 600;
            border: none;
        }
        .badge-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .chart-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            height: 400px;
        }
        .status-paid { background: #d4edda; color: #155724; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-active { background: #d1ecf1; color: #0c5460; }
        .status-used { background: #f8d7da; color: #721c24; }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; }
        }
    </style>
</head>
<body>
    <!-- 導航欄 -->
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid">
            <span class="navbar-brand text-white">
                <i class="fab fa-telegram-plane me-2"></i>TG旺企業管理系統 (機器人數據整合)
            </span>
            <div class="navbar-nav ms-auto">
                <span class="text-white me-3">
                    <i class="fas fa-user-circle me-1"></i>{{ username }} ({{ user_role_name }})
                </span>
                <span class="text-white me-3" id="current-time"></span>
                <a href="/logout" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-sign-out-alt me-1"></i>登出
                </a>
            </div>
        </div>
    </nav>

    <!-- 側邊欄 -->
    <div class="sidebar">
        <div class="nav flex-column pt-3">
            <a class="nav-link active" href="javascript:void(0)" onclick="switchTab('dashboard')">
                <i class="fas fa-tachometer-alt me-2"></i>儀表板
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('orders')">
                <i class="fas fa-shopping-cart me-2"></i>TG機器人訂單
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('activations')">
                <i class="fas fa-key me-2"></i>激活碼管理
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('collected-data')">
                <i class="fas fa-database me-2"></i>採集數據
            </a>
            {% if 'all' in permissions %}
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('statistics')">
                <i class="fas fa-chart-pie me-2"></i>統計分析
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('users')">
                <i class="fas fa-users me-2"></i>用戶管理
            </a>
            {% endif %}
        </div>
    </div>

    <!-- 主要內容 -->
    <div class="main-content">
        <!-- 儀表板概覽 -->
        <div id="dashboard-tab" class="tab-content active">
            <div class="row mb-4">
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-revenue">0 TRX</div>
                                <div class="stat-label">總收入</div>
                            </div>
                            <i class="fas fa-dollar-sign fa-2x text-success"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-orders">0</div>
                                <div class="stat-label">總訂單數</div>
                            </div>
                            <i class="fas fa-shopping-cart fa-2x text-primary"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-activations">0</div>
                                <div class="stat-label">激活碼總數</div>
                            </div>
                            <i class="fas fa-key fa-2x text-warning"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="collected-members">0</div>
                                <div class="stat-label">採集成員數</div>
                            </div>
                            <i class="fas fa-users fa-2x text-info"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-8 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">收入趨勢</h5>
                        <canvas id="revenueChart"></canvas>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">方案分布</h5>
                        <canvas id="planChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- TG機器人訂單 -->
        <div id="orders-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-shopping-cart me-2"></i>TG機器人訂單</h3>
                <button class="btn btn-success" onclick="refreshOrders()">
                    <i class="fas fa-refresh me-1"></i>刷新數據
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>訂單編號</th>
                                <th>用戶ID</th>
                                <th>方案類型</th>
                                <th>金額</th>
                                <th>貨幣</th>
                                <th>狀態</th>
                                <th>交易哈希</th>
                                <th>創建時間</th>
                                <th>到期時間</th>
                            </tr>
                        </thead>
                        <tbody id="orders-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 激活碼管理 -->
        <div id="activations-tab" class="tab-content">
            <div class="alert alert-info">
                <h6><i class="fas fa-info-circle me-2"></i>設備ID說明</h6>
                <p class="mb-0">設備ID是軟件運行設備的唯一標識符，由MAC地址和主機名生成的16位哈希值。每個激活碼只能在一台設備上使用，確保軟件使用的安全性。</p>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-key me-2"></i>激活碼管理</h3>
                <div>
                    <select class="form-select d-inline-block me-2" style="width: 120px;" onchange="filterActivationsByStatus(this.value)">
                        <option value="all">全部狀態</option>
                        <option value="unused">未使用</option>
                        <option value="used">已使用</option>
                        <option value="disabled">已停權</option>
                    </select>
                    <input type="text" class="form-control d-inline-block" placeholder="搜索激活碼..." id="activation-search" style="width: 200px;">
                    <button class="btn btn-info ms-2" onclick="searchActivations()">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-success ms-2" onclick="refreshActivations()">
                        <i class="fas fa-refresh me-1"></i>刷新
                    </button>
                    <button class="btn btn-warning ms-2" onclick="exportActivationCodes()">
                        <i class="fas fa-download me-1"></i>匯出
                    </button>
                </div>
            </div>
            
            <!-- 激活碼統計信息 -->
            <div class="row mb-3">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <h5 id="total-codes">0</h5>
                            <p class="mb-0">總激活碼數</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <h5 id="unused-codes">0</h5>
                            <p class="mb-0">未使用</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <h5 id="used-codes">0</h5>
                            <p class="mb-0">已使用</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-danger text-white">
                        <div class="card-body">
                            <h5 id="disabled-codes">0</h5>
                            <p class="mb-0">已停權</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>方案類型</th>
                                <th>狀態</th>
                                <th>有效期</th>
                                <th>使用狀態</th>
                                <th>設備ID</th>
                                <th>使用時間</th>
                                <th>創建時間</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="activations-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 採集數據 -->
        <div id="collected-data-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-database me-2"></i>採集數據管理</h3>
                <button class="btn btn-success" onclick="refreshCollectedData()">
                    <i class="fas fa-refresh me-1"></i>刷新數據
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>設備信息</th>
                                <th>採集方法</th>
                                <th>目標群組</th>
                                <th>採集數量</th>
                                <th>上傳時間</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="collected-data-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if 'all' in permissions %}
        <!-- 統計分析 -->
        <div id="statistics-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-chart-pie me-2"></i>統計分析</h3>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">每日訂單趨勢</h5>
                        <canvas id="dailyOrdersChart"></canvas>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">激活碼使用率</h5>
                        <canvas id="activationRateChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 用戶管理 -->
        <div id="users-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-users me-2"></i>用戶管理</h3>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>用戶ID</th>
                                <th>用戶名稱</th>
                                <th>註冊時間</th>
                                <th>狀態</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="users-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 全局錯誤處理
        window.onerror = function(msg, url, lineNo, columnNo, error) {
            console.error('JavaScript錯誤:', {
                message: msg,
                source: url,
                lineno: lineNo,
                colno: columnNo,
                error: error
            });
            return false;
        };
        
        let currentTab = 'dashboard';
        
        // HTML轉義函數，防止特殊字符破壞JavaScript語法
        function escapeHtml(str) {
            if (str === null || str === undefined) {
                return '';
            }
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;')
                .replace(/\\r\\n/g, ' ')
                .replace(/\\n/g, ' ')
                .replace(/\\r/g, ' ')
                .replace(/\\t/g, ' ');
        }
        
        // 時間更新
        function updateTime() {
            document.getElementById('current-time').textContent = 
                new Date().toLocaleString('zh-TW');
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        // 標籤切換
        function switchTab(tabName) {
            // 更新導航狀態
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            
            // 找到被點擊的連結並設為活動狀態
            const clickedLink = document.querySelector(`[onclick*="switchTab('${tabName}')"]`);
            if (clickedLink) {
                clickedLink.classList.add('active');
            }
            
            // 更新內容顯示
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            const tabElement = document.getElementById(tabName + '-tab');
            if (tabElement) {
                tabElement.classList.add('active');
            }
            
            currentTab = tabName;
            loadTabData(tabName);
        }
        
        // 載入數據
        async function loadTabData(tabName) {
            try {
                switch(tabName) {
                    case 'dashboard':
                        await loadDashboardData();
                        break;
                    case 'orders':
                        await loadOrdersData();
                        break;
                    case 'activations':
                        await loadActivationsData();
                        break;
                    case 'collected-data':
                        await loadCollectedData();
                        break;
                    case 'statistics':
                        await loadStatisticsData();
                        break;
                    case 'users':
                        await loadUsersData();
                        break;
                }
            } catch (error) {
                console.error('載入數據失敗:', error);
            }
        }
        
        // 載入儀表板數據
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                document.getElementById('total-revenue').textContent = data.total_revenue + ' TRX';
                document.getElementById('total-orders').textContent = data.total_orders;
                document.getElementById('total-activations').textContent = data.total_activations;
                document.getElementById('collected-members').textContent = data.collected_members;
                
            } catch (error) {
                console.error('載入儀表板數據失敗:', error);
            }
        }
        
        // 載入訂單數據
        async function loadOrdersData() {
            try {
                const response = await fetch('/api/orders');
                const data = await response.json();
                updateOrdersTable(data.orders || []);
            } catch (error) {
                console.error('載入訂單數據失敗:', error);
            }
        }
        
        // 載入激活碼數據
        async function loadActivationsData() {
            try {
                const response = await fetch('/api/activation_codes');
                const data = await response.json();
                updateActivationsTable(data.codes || []);
            } catch (error) {
                console.error('載入激活碼數據失敗:', error);
            }
        }
        
        function updateActivationsTable(codes) {
            const tbody = document.getElementById('activations-tbody');
            tbody.innerHTML = '';
            
            // 統計數據
            let totalCodes = codes.length;
            let usedCodes = 0;
            let unusedCodes = 0;
            let disabledCodes = 0;
            
            codes.forEach(code => {
                const row = document.createElement('tr');
                
                // 狀態顏色
                const statusClass = code.disabled ? 'text-danger' : (code.used ? 'text-warning' : 'text-success');
                const statusText = code.disabled ? '已停權' : (code.used ? '已使用' : '未使用');
                
                // 方案類型顯示
                const planNames = {
                    'trial': '試用版',
                    'weekly': '週方案',
                    'monthly': '月方案',
                    'premium': '旗艦版',
                    'master': '萬能密鑰'
                };
                const planName = planNames[code.plan_type] || code.plan_type;
                
                // 設備ID顯示
                const deviceId = code.used_by_device || '-';
                const deviceIdShort = deviceId.length > 16 ? deviceId.substring(0, 16) + '...' : deviceId;
                
                // 使用時間顯示
                const usedAt = code.used_at ? new Date(code.used_at).toLocaleString() : '-';
                
                // 統計計數
                if (code.disabled) {
                    disabledCodes++;
                } else if (code.used) {
                    usedCodes++;
                } else {
                    unusedCodes++;
                }
                
                row.innerHTML = `
                    <td><code>${escapeHtml(code.code)}</code></td>
                    <td><span class="badge bg-primary">${escapeHtml(planName)}</span></td>
                    <td><span class="badge ${code.disabled ? 'bg-danger' : 'bg-success'}">${code.disabled ? '已停權' : '正常'}</span></td>
                    <td>${code.days === 99999 ? '永久' : code.days + '天'}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td title="${escapeHtml(deviceId)}"><code>${escapeHtml(deviceIdShort)}</code></td>
                    <td>${usedAt}</td>
                    <td>${code.created_at ? new Date(code.created_at).toLocaleString() : '-'}</td>
                    <td>
                        ${code.disabled ? 
                            '<button class="btn btn-success btn-sm" data-code="' + escapeHtml(code.code) + '" onclick="enableActivationCode(this.dataset.code)">恢復</button>' :
                            '<button class="btn btn-danger btn-sm" data-code="' + escapeHtml(code.code) + '" onclick="disableActivationCode(this.dataset.code)">停權</button>'
                        }
                        <button class="btn btn-info btn-sm" data-code="` + escapeHtml(code.code) + `" onclick="viewCodeDetails(this.dataset.code)">詳情</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
            
            // 更新統計顯示
            document.getElementById('total-codes').textContent = totalCodes;
            document.getElementById('unused-codes').textContent = unusedCodes;
            document.getElementById('used-codes').textContent = usedCodes;
            document.getElementById('disabled-codes').textContent = disabledCodes;
        }
        
        async function disableActivationCode(code) {
            const reason = prompt('請輸入停權原因:', '違規使用');
            if (!reason) return;
            
            try {
                const response = await fetch('/api/disable_activation_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        activation_code: code,
                        reason: reason
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('激活碼已停權');
                    loadActivationsData();
                } else {
                    alert('停權失敗: ' + data.error);
                }
            } catch (error) {
                console.error('停權失敗:', error);
                alert('停權失敗');
            }
        }
        
        async function enableActivationCode(code) {
            if (!confirm('確定要恢復此激活碼嗎？')) return;
            
            try {
                const response = await fetch('/api/enable_activation_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        activation_code: code
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('激活碼已恢復');
                    loadActivationsData();
                } else {
                    alert('恢復失敗: ' + data.error);
                }
            } catch (error) {
                console.error('恢復失敗:', error);
                alert('恢復失敗');
            }
        }
        
        async function viewCodeDetails(code) {
            try {
                const response = await fetch('/api/activation_code_details/' + code);
                const data = await response.json();
                
                if (data.success) {
                    const codeInfo = data.code_info;
                    
                    // 格式化信息
                    const planNames = {
                        'trial': '試用版',
                        'weekly': '週方案',
                        'monthly': '月方案',
                        'premium': '旗艦版',
                        'master': '萬能密鑰'
                    };
                    const planName = planNames[codeInfo.plan_type] || codeInfo.plan_type;
                    
                    const modalContent = `
                        <h5>激活碼詳情</h5>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>激活碼:</strong> <code>${escapeHtml(codeInfo.code)}</code></p>
                                <p><strong>方案類型:</strong> <span class="badge bg-primary">${escapeHtml(planName)}</span></p>
                                <p><strong>有效期:</strong> ${codeInfo.days === 99999 ? '永久' : codeInfo.days + '天'}</p>
                                <p><strong>狀態:</strong> <span class="badge ${codeInfo.disabled ? 'bg-danger' : 'bg-success'}">${codeInfo.disabled ? '已停權' : '正常'}</span></p>
                                <p><strong>使用狀態:</strong> <span class="badge ${codeInfo.used ? 'bg-warning' : 'bg-success'}">${codeInfo.used ? '已使用' : '未使用'}</span></p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>創建時間:</strong> ${codeInfo.created_at ? new Date(codeInfo.created_at).toLocaleString() : '-'}</p>
                                <p><strong>使用時間:</strong> ${codeInfo.used_at ? new Date(codeInfo.used_at).toLocaleString() : '-'}</p>
                                <p><strong>到期時間:</strong> ${codeInfo.expires_at ? new Date(codeInfo.expires_at).toLocaleString() : '-'}</p>
                                <p><strong>設備ID:</strong> <code>${escapeHtml(codeInfo.used_by_device || '-')}</code></p>
                                <p><strong>用戶ID:</strong> ${escapeHtml(codeInfo.user_id || '-')}</p>
                            </div>
                        </div>
                        ${codeInfo.disabled ? 
                            '<div class="alert alert-danger">' +
                                '<strong>停權信息:</strong><br>' +
                                '停權時間: ' + (codeInfo.disabled_at ? new Date(codeInfo.disabled_at).toLocaleString() : '-') + '<br>' +
                                '停權原因: ' + (codeInfo.disabled_reason || '-') + '<br>' +
                                '操作者: ' + (codeInfo.disabled_by || '-') +
                            '</div>'
                        : ''}
                    `;
                    
                    // 顯示模態框
                    document.getElementById('code-details-content').innerHTML = modalContent;
                    const modal = new bootstrap.Modal(document.getElementById('code-details-modal'));
                    modal.show();
                } else {
                    alert('獲取激活碼詳情失敗: ' + data.error);
                }
            } catch (error) {
                console.error('獲取激活碼詳情失敗:', error);
                alert('獲取激活碼詳情失敗');
            }
        }
        
        function refreshActivations() {
            loadActivationsData();
        }
        
        function searchActivations() {
            const searchTerm = document.getElementById('activation-search').value.toLowerCase();
            const rows = document.querySelectorAll('#activations-tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
        
        function filterActivationsByStatus(status) {
            const rows = document.querySelectorAll('#activations-tbody tr');
            
            rows.forEach(row => {
                if (status === 'all') {
                    row.style.display = '';
                } else {
                    const statusCell = row.cells[4]; // 使用狀態列
                    const statusText = statusCell.textContent.toLowerCase();
                    
                    if (status === 'used' && statusText.includes('已使用')) {
                        row.style.display = '';
                    } else if (status === 'unused' && statusText.includes('未使用')) {
                        row.style.display = '';
                    } else if (status === 'disabled' && statusText.includes('已停權')) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
        }
        
        function exportActivationCodes() {
            const rows = document.querySelectorAll('#activations-tbody tr');
            const csvContent = [];
            
            // 添加標題行
            csvContent.push('激活碼,方案類型,狀態,有效期,使用狀態,設備ID,使用時間,創建時間');
            
            rows.forEach(row => {
                if (row.style.display !== 'none') {
                    const cells = row.cells;
                    const rowData = [];
                    
                    for (let i = 0; i < cells.length - 1; i++) { // 排除操作列
                        rowData.push(cells[i].textContent.trim());
                    }
                    
                    csvContent.push(rowData.join(','));
                }
            });
            
            // 創建並下載CSV文件
            const blob = new Blob([csvContent.join('\\n')], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', 'activation_codes_' + new Date().toISOString().split('T')[0] + '.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // 載入採集數據
        async function loadCollectedData() {
            try {
                const response = await fetch('/api/collected-data');
                const data = await response.json();
                updateCollectedDataTable(data.collected_data || []);
            } catch (error) {
                console.error('載入採集數據失敗:', error);
            }
        }
        
        // 載入統計數據
        async function loadStatisticsData() {
            try {
                const response = await fetch('/api/statistics');
                const data = await response.json();
                
                // 顯示統計數據
                console.log('統計數據:', data);
                
            } catch (error) {
                console.error('載入統計數據失敗:', error);
            }
        }
        
        // 載入用戶數據
        async function loadUsersData() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                let tbody = document.getElementById('users-tbody');
                if (tbody) {
                    tbody.innerHTML = '';
                    
                    data.users.forEach(user => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${escapeHtml(user.id)}</td>
                            <td>${escapeHtml(user.username)}</td>
                            <td>${escapeHtml(user.created_at)}</td>
                            <td><span class="badge bg-success">正常</span></td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" data-userid="${escapeHtml(user.id)}" onclick="viewUserDetails(this.dataset.userid)">詳情</button>
                            </td>
                        `;
                        tbody.appendChild(row);
                    });
                }
                
            } catch (error) {
                console.error('載入用戶數據失敗:', error);
            }
        }
        
        // 更新訂單表格
        function updateOrdersTable(orders) {
            const tbody = document.getElementById('orders-tbody');
            tbody.innerHTML = '';
            
            orders.forEach(order => {
                const row = `
                    <tr>
                        <td><code>${escapeHtml(order.order_id)}</code></td>
                        <td>${escapeHtml(order.user_id)}</td>
                        <td><span class="badge bg-primary">${escapeHtml(order.plan_type_chinese || '')}</span></td>
                        <td>${escapeHtml(order.amount)}</td>
                        <td>${escapeHtml(order.currency)}</td>
                        <td><span class="badge ${order.status === 'paid' ? 'status-paid' : 'status-pending'}">${order.status === 'paid' ? '已付款' : '待付款'}</span></td>
                        <td><small><code>${order.tx_hash ? escapeHtml(order.tx_hash.slice(0, 16)) + '...' : 'N/A'}</code></small></td>
                        <td>${order.created_at ? new Date(order.created_at).toLocaleDateString('zh-TW') : '-'}</td>
                        <td>${order.expires_at ? new Date(order.expires_at).toLocaleDateString('zh-TW') : '-'}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新採集數據表格
        function updateCollectedDataTable(collectedData) {
            const tbody = document.getElementById('collected-data-tbody');
            tbody.innerHTML = '';
            
            collectedData.forEach(data => {
                const row = `
                    <tr>
                        <td><code>${escapeHtml(data.activation_code)}</code></td>
                        <td><small>${escapeHtml(data.device_info || '')}</small></td>
                        <td>${escapeHtml(data.collection_method || '')}</td>
                        <td>${escapeHtml(data.target_groups || '')}</td>
                        <td><span class="badge bg-success">${escapeHtml(data.total_collected || '0')}</span></td>
                        <td>${data.upload_timestamp ? new Date(data.upload_timestamp).toLocaleDateString('zh-TW') : '-'}</td>
                        <td>
                            <button class="btn btn-sm btn-info" data-code="${escapeHtml(data.activation_code)}" onclick="viewCollectedDetails(this.dataset.code)">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 按鈕功能
        function refreshOrders() {
            loadOrdersData();
        }
        
        function refreshCollectedData() {
            loadCollectedData();
        }
        
        function viewCollectedDetails(activationCode) {
            alert('查看採集詳情: ' + activationCode);
        }
        
        function viewUserDetails(userId) {
            alert('查看用戶詳情: ' + userId);
        }
        
        // 初始化
        window.onload = function() {
            loadDashboardData();
        };
    </script>
    
    <!-- 激活碼詳情模態框 -->
    <div class="modal fade" id="code-details-modal" tabindex="-1" aria-labelledby="code-details-modal-label" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="code-details-modal-label">激活碼詳情</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" id="code-details-content">
                    <!-- 動態載入內容 -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">關閉</button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# API路由
@app.route('/api/dashboard')
def api_dashboard():
    """儀表板API - 整合機器人數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        uploaded_data = get_uploaded_data()
        
        # 計算統計數據
        total_revenue = bot_db.get('statistics', {}).get('total_revenue', 0)
        total_orders = len(bot_db.get('orders', {}))
        total_activations = len(bot_db.get('activation_codes', {}))
        
        # 計算採集成員總數
        collected_members = 0
        for data in uploaded_data:
            if 'collected_members' in data:
                collected_members += len(data['collected_members'])
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'total_activations': total_activations,
            'collected_members': collected_members
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def api_orders():
    """訂單API - 機器人訂單數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        orders = []
        
        for order_id, order_data in bot_db.get('orders', {}).items():
            orders.append({
                'order_id': order_data.get('order_id'),
                'user_id': order_data.get('user_id'),
                'plan_type': order_data.get('plan_type'),
                'plan_type_chinese': get_plan_type_chinese(order_data.get('plan_type')),
                'amount': order_data.get('amount'),
                'currency': order_data.get('currency'),
                'status': order_data.get('status'),
                'tx_hash': order_data.get('tx_hash'),
                'created_at': order_data.get('created_at'),
                'expires_at': order_data.get('expires_at')
            })
        
        # 按創建時間排序
        orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'orders': orders})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activations')
def api_activations():
    """激活碼API - 機器人激活碼數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        activations = []
        
        for code, code_data in bot_db.get('activation_codes', {}).items():
            activations.append({
                'activation_code': code_data.get('activation_code'),
                'plan_type': code_data.get('plan_type'),
                'plan_type_chinese': get_plan_type_chinese(code_data.get('plan_type')),
                'user_id': code_data.get('user_id'),
                'order_id': code_data.get('order_id'),
                'days': code_data.get('days'),
                'used': code_data.get('used', False),
                'created_at': code_data.get('created_at'),
                'expires_at': code_data.get('expires_at'),
                'used_by_device': code_data.get('used_by_device')
            })
        
        # 按創建時間排序
        activations.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'activations': activations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/collected-data')
def api_collected_data():
    """採集數據API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        uploaded_data = get_uploaded_data()
        collected_data = []
        
        for data in uploaded_data:
            device_info = data.get('device_info', {})
            
            # 支援兩種數據格式：collection_info 和 collections
            collection_info = data.get('collection_info', {})
            collections = data.get('collections', [])
            
            # 如果是新格式（collections數組）
            if collections and isinstance(collections, list):
                for collection in collections:
                    collected_data.append({
                        'activation_code': data.get('activation_code'),
                        'device_info': f"{device_info.get('hostname', 'N/A')} ({device_info.get('platform', 'N/A')})",
                        'collection_method': collection.get('method', '活躍用戶採集'),
                        'target_groups': collection.get('group_name', collection.get('target', 'N/A')),
                        'total_collected': collection.get('members_count', collection.get('total', 0)),
                        'upload_timestamp': collection.get('timestamp', data.get('upload_time', data.get('upload_timestamp')))
                    })
            # 如果是舊格式（collection_info對象）
            else:
                collected_data.append({
                    'activation_code': data.get('activation_code'),
                    'device_info': f"{device_info.get('hostname', 'N/A')} ({device_info.get('platform', 'N/A')})",
                    'collection_method': collection_info.get('collection_method', 'N/A'),
                    'target_groups': ', '.join(collection_info.get('target_groups', [])),
                    'total_collected': collection_info.get('total_collected', 0),
                    'upload_timestamp': data.get('upload_timestamp')
                })
        
        # 按上傳時間排序
        collected_data.sort(key=lambda x: x['upload_timestamp'], reverse=True)
        
        return jsonify({'collected_data': collected_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 基本路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登入"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username in ADMIN_USERS and ADMIN_USERS[username] == password_hash:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='帳號或密碼錯誤')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/')
def index():
    """首頁"""
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/api/activation_codes')
def api_activation_codes():
    """獲取激活碼列表API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        activation_codes = bot_db.get('activation_codes', {})
        
        # 格式化激活碼列表
        codes_list = []
        for code, info in activation_codes.items():
            codes_list.append({
                'code': code,
                'plan_type': info.get('plan_type', 'unknown'),
                'days': info.get('days', 0),
                'used': info.get('used', False),
                'disabled': info.get('disabled', False),
                'created_at': info.get('created_at', ''),
                'used_at': info.get('used_at', ''),
                'used_by_device': info.get('used_by_device', ''),
                'disabled_at': info.get('disabled_at', ''),
                'disabled_by': info.get('disabled_by', ''),
                'expires_at': info.get('expires_at', '')
            })
        
        # 按創建時間排序
        codes_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'codes': codes_list,
            'total': len(codes_list)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/disable_activation_code', methods=['POST'])
def api_disable_activation_code():
    """停權激活碼API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        activation_code = data.get('activation_code')
        reason = data.get('reason', '管理員停權')
        
        if not activation_code:
            return jsonify({'error': '激活碼不能為空'}), 400
        
        # 使用數據庫適配器獲取激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 使用專門的狀態更新方法
        success = db_adapter.update_activation_code_status(
            activation_code, 
            disabled=True, 
            disabled_by=session.get('username', 'admin'), 
            reason=reason
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'激活碼 {activation_code} 已被停權'
            })
        else:
            return jsonify({'error': '停權失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/enable_activation_code', methods=['POST'])
def api_enable_activation_code():
    """恢復激活碼API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        activation_code = data.get('activation_code')
        
        if not activation_code:
            return jsonify({'error': '激活碼不能為空'}), 400
        
        # 使用數據庫適配器獲取激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 使用專門的狀態更新方法
        success = db_adapter.update_activation_code_status(
            activation_code, 
            disabled=False, 
            disabled_by=session.get('username', 'admin'), 
            reason=None
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'激活碼 {activation_code} 已恢復'
            })
        else:
            return jsonify({'error': '恢復失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_software_data', methods=['POST'])
def api_upload_software_data():
    """接收軟件上傳的數據API（支持PostgreSQL存儲採集數據）"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({'error': '無效的API密鑰'}), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id')
        software_data = data.get('data', {})
        
        if not activation_code or not device_id:
            return jsonify({'error': '缺少必要參數'}), 400
        
        # 驗證激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 檢查是否被停權
        if code_info.get('disabled', False):
            return jsonify({'error': '激活碼已被停權，軟件已停止'}), 403
        
        # 保存軟件數據
        software_record = {
            'activation_code': activation_code,
            'device_id': device_id,
            'device_info': data.get('device_info', {}),
            'ip_location': data.get('ip_location', {}),
            'upload_time': datetime.now().isoformat(),
            'accounts': software_data.get('accounts', []),
            'collections': software_data.get('collections', []),
            'invitations': software_data.get('invitations', []),
            'statistics': software_data.get('statistics', {}),
            'status': software_data.get('status', 'running')
        }
        
        # 如果有採集數據，同時保存到 PostgreSQL 的 collection_data 表
        collections = software_data.get('collections', [])
        if collections:
            db_url = os.environ.get('DATABASE_URL')
            if db_url:
                try:
                    import psycopg2
                    import json as json_lib
                    
                    conn = psycopg2.connect(db_url)
                    cur = conn.cursor()
                    
                    # 檢查表是否存在
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'collection_data'
                        )
                    """)
                    if cur.fetchone()[0]:
                        # 保存每個採集記錄
                        for collection in collections:
                            members = collection.get('members', [])
                            if members:
                                # 從成員數據中提取群組名稱
                                group_name = collection.get('target_group', 'Unknown')
                                if group_name == 'unknown' and members:
                                    # 嘗試從第一個成員獲取群組名稱
                                    first_member = members[0] if isinstance(members[0], dict) else {}
                                    group_name = first_member.get('group_name', group_name)
                                
                                cur.execute("""
                                    INSERT INTO collection_data 
                                    (activation_code, device_id, device_info, ip_location, 
                                     group_name, group_link, collection_method, members_count, members_data)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    activation_code,
                                    device_id,
                                    json_lib.dumps(data.get('device_info', {}), ensure_ascii=False),
                                    json_lib.dumps(data.get('ip_location', {}), ensure_ascii=False),
                                    group_name,
                                    '',  # 群組鏈接
                                    '活躍用戶採集',
                                    collection.get('collected_count', len(members)),
                                    json_lib.dumps(members, ensure_ascii=False)
                                ))
                        
                        conn.commit()
                        logger.info(f"成功保存 {len(collections)} 條採集記錄到 PostgreSQL")
                    
                    cur.close()
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"保存到 PostgreSQL 失敗: {e}")
        
        # 保存到上傳數據目錄（作為備份）
        upload_file = os.path.join(UPLOAD_DATA_DIR, f"software_{device_id}_{int(datetime.now().timestamp())}.json")
        os.makedirs(UPLOAD_DATA_DIR, exist_ok=True)
        
        with open(upload_file, 'w', encoding='utf-8') as f:
            json.dump(software_record, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '數據上傳成功',
            'activation_status': 'active' if not code_info.get('disabled', False) else 'disabled'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_collection_data', methods=['POST'])
def api_upload_collection_data():
    """接收採集數據上傳API（使用PostgreSQL存儲）"""
    try:
        logger.info(f"收到採集數據上傳請求")
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id')
        members_data = data.get('members', [])
        group_info = data.get('group_info', {})
        
        if not activation_code:
            return jsonify({'error': '缺少激活碼'}), 400
        
        logger.info(f"激活碼: {activation_code}, 成員數: {len(members_data)}")
        
        # 驗證激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 嘗試保存到 PostgreSQL
        saved_to_db = False
        db_url = os.environ.get('DATABASE_URL')
        
        if db_url:
            try:
                import psycopg2
                import json as json_lib
                
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                
                # 檢查表是否存在
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'collection_data'
                    )
                """)
                table_exists = cur.fetchone()[0]
                
                if not table_exists:
                    # 創建表
                    logger.info("創建 collection_data 表...")
                    cur.execute("""
                        CREATE TABLE collection_data (
                            id SERIAL PRIMARY KEY,
                            activation_code VARCHAR(50) NOT NULL,
                            device_id VARCHAR(100),
                            device_info TEXT,
                            ip_location TEXT,
                            group_name VARCHAR(255),
                            group_link TEXT,
                            collection_method VARCHAR(100) DEFAULT '活躍用戶採集',
                            members_count INTEGER DEFAULT 0,
                            members_data TEXT,
                            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute("CREATE INDEX idx_collection_activation_code ON collection_data(activation_code)")
                    conn.commit()
                
                # 插入數據
                cur.execute("""
                    INSERT INTO collection_data 
                    (activation_code, device_id, device_info, ip_location, 
                     group_name, group_link, members_count, members_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    activation_code,
                    device_id or 'unknown',
                    json_lib.dumps(data.get('device_info', {}), ensure_ascii=False),
                    json_lib.dumps(data.get('ip_location', {}), ensure_ascii=False),
                    group_info.get('name', 'Unknown'),
                    group_info.get('link', ''),
                    len(members_data),
                    json_lib.dumps(members_data, ensure_ascii=False)
                ))
                
                conn.commit()
                cur.close()
                conn.close()
                
                saved_to_db = True
                logger.info(f"成功保存到 PostgreSQL: {activation_code}")
                
            except Exception as e:
                logger.error(f"PostgreSQL 保存失敗: {e}")
                saved_to_db = False
        
        # 如果數據庫保存失敗，降級到文件系統
        if not saved_to_db:
            logger.info("降級到文件系統存儲")
            collection_record = {
                'activation_code': activation_code,
                'device_id': device_id or 'unknown',
                'device_info': data.get('device_info', {}),
                'ip_location': data.get('ip_location', {}),
                'upload_time': datetime.now().isoformat(),
                'collections': [{
                    'group_name': group_info.get('name', 'Unknown'),
                    'group_link': group_info.get('link', ''),
                    'method': '活躍用戶採集',
                    'members_count': len(members_data),
                    'members': members_data,
                    'timestamp': datetime.now().isoformat()
                }]
            }
            
            # 保存到上傳數據目錄
            upload_file = os.path.join(UPLOAD_DATA_DIR, f"collection_{activation_code}_{int(datetime.now().timestamp())}.json")
            os.makedirs(UPLOAD_DATA_DIR, exist_ok=True)
            
            with open(upload_file, 'w', encoding='utf-8') as f:
                json.dump(collection_record, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'成功上傳 {len(members_data)} 個成員數據',
            'storage': 'postgresql' if saved_to_db else 'filesystem'
        })
        
    except Exception as e:
        logger.error(f"上傳採集數據失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync_activation_code', methods=['POST'])
def api_sync_activation_code():
    """同步激活碼到雲端數據庫"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({'error': '無效的API密鑰'}), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        code_data = data.get('code_data', {})
        
        if not activation_code or not code_data:
            return jsonify({'error': '缺少必要參數'}), 400
        
        # 檢查激活碼是否已存在
        existing_code = db_adapter.get_activation_code(activation_code)
        if existing_code:
            return jsonify({'error': '激活碼已存在'}), 409
        
        # 保存激活碼到雲端數據庫
        success = db_adapter.save_activation_code(activation_code, code_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': '激活碼同步成功',
                'activation_code': activation_code
            })
        else:
            return jsonify({'error': '同步失敗'}), 500
    
    except Exception as e:
        logger.error(f"同步激活碼失敗: {e}")
        return jsonify({'error': '同步失敗'}), 500

@app.route('/api/statistics')
def api_statistics():
    """統計分析API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        
        # 計算統計數據
        stats = {
            'total_users': len(bot_db.get('users', {})),
            'total_orders': len(bot_db.get('orders', {})),
            'total_revenue': bot_db.get('statistics', {}).get('total_revenue', 0),
            'activation_usage': {
                'total': len(bot_db.get('activation_codes', {})),
                'used': sum(1 for code in bot_db.get('activation_codes', {}).values() if code.get('used', False)),
                'disabled': sum(1 for code in bot_db.get('activation_codes', {}).values() if code.get('disabled', False))
            }
        }
        
        return jsonify({'statistics': stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def api_users():
    """用戶管理API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        users_data = bot_db.get('users', {})
        
        # 格式化用戶數據
        users = []
        for user_id, user_info in users_data.items():
            users.append({
                'id': user_id,
                'username': user_info.get('username', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'created_at': user_info.get('created_at', ''),
                'language': user_info.get('language', ''),
                'is_premium': user_info.get('is_premium', False)
            })
        
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activation_code_details/<activation_code>')
def api_activation_code_details(activation_code):
    """獲取激活碼詳情API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # 從共享數據庫獲取激活碼詳情
        code_info = db_adapter.get_activation_code(activation_code)
        
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 格式化返回數據
        result = {
            'code': activation_code,
            'plan_type': code_info.get('plan_type', 'unknown'),
            'days': code_info.get('days', 0),
            'used': code_info.get('used', False),
            'disabled': code_info.get('disabled', False),
            'created_at': code_info.get('created_at', ''),
            'used_at': code_info.get('used_at', ''),
            'used_by_device': code_info.get('used_by_device', ''),
            'disabled_at': code_info.get('disabled_at', ''),
            'disabled_by': code_info.get('disabled_by', ''),
            'disabled_reason': code_info.get('disabled_reason', ''),
            'expires_at': code_info.get('expires_at', ''),
            'user_id': code_info.get('user_id', ''),
            'order_id': code_info.get('order_id', '')
        }
        
        return jsonify({
            'success': True,
            'code_info': result
        })
    
    except Exception as e:
        logger.error(f"獲取激活碼詳情失敗: {e}")
        return jsonify({'error': '獲取激活碼詳情失敗'}), 500

@app.route('/dashboard')
def dashboard():
    """儀表板"""
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    
    username = session.get('username')
    user_role_info = USER_ROLES.get(username, USER_ROLES['agent'])
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                username=username,
                                user_role=username,
                                user_role_name=user_role_info['name'],
                                permissions=user_role_info['permissions'])

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

# ========== API端點：供TG旺軟件使用 ==========

@app.route('/api/health', methods=['GET'])
def api_health():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "TG旺企業管理系統"
    })

@app.route('/api/verify_activation', methods=['POST'])
def api_verify_activation():
    """API: 驗證激活碼"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "valid": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id', 'unknown')
        
        if not activation_code:
            return jsonify({
                "valid": False,
                "message": "缺少激活碼"
            }), 400
        
        # 讀取機器人數據庫
        bot_data = get_bot_database()
        code_info = bot_data.get('activation_codes', {}).get(activation_code)
        
        if not code_info:
            return jsonify({
                "valid": False,
                "message": "激活碼不存在"
            })
        
        # 檢查是否被停權
        if code_info.get('disabled', False):
            return jsonify({
                "valid": False,
                "message": f"激活碼已被停權，停權時間: {code_info.get('disabled_at', 'unknown')}，原因: {code_info.get('disabled_reason', '管理員停權')}"
            })
        
        if code_info.get('used', False):
            return jsonify({
                "valid": False,
                "message": f"激活碼已於 {code_info.get('used_at', 'unknown')} 使用過"
            })
        
        # 檢查是否過期
        expires_at = datetime.fromisoformat(code_info['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({
                "valid": False,
                "message": f"激活碼已於 {expires_at.strftime('%Y-%m-%d %H:%M:%S')} 過期"
            })
        
        # 激活碼有效
        return jsonify({
            "valid": True,
            "message": "激活碼有效",
            "data": {
                "plan_type": code_info['plan_type'],
                "days": code_info['days'],
                "expires_at": code_info['expires_at'],
                "created_at": code_info['created_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            "valid": False,
            "message": f"驗證錯誤: {str(e)}"
        }), 500

@app.route('/api/use_activation', methods=['POST'])
def api_use_activation():
    """API: 使用激活碼（標記為已使用）"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "success": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id', 'unknown')
        
        if not activation_code:
            return jsonify({
                "success": False,
                "message": "缺少激活碼"
            }), 400
        
        # 讀取機器人數據庫
        bot_data = get_bot_database()
        code_info = bot_data.get('activation_codes', {}).get(activation_code)
        
        if not code_info:
            return jsonify({
                "success": False,
                "message": "激活碼不存在"
            })
        
        if code_info.get('used', False):
            return jsonify({
                "success": False,
                "message": "激活碼已使用過"
            })
        
        # 標記為已使用
        code_info['used'] = True
        code_info['used_at'] = datetime.now().isoformat()
        code_info['used_by_device'] = device_id
        
        # 保存到數據庫
        with open(BOT_DATABASE_PATH, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": f"激活成功 - {code_info['plan_type']} ({code_info['days']}天)",
            "data": {
                "plan_type": code_info['plan_type'],
                "days": code_info['days'],
                "expires_at": code_info['expires_at'],
                "used_at": code_info['used_at'],
                "device_id": device_id
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"使用錯誤: {str(e)}"
        }), 500


@app.route('/sync/activation_code', methods=['POST'])
def sync_activation_code():
    """同步激活碼端點 - 供機器人雲端同步使用"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "success": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        code_data = data.get('code_data')
        
        if not activation_code or not code_data:
            return jsonify({
                "success": False,
                "message": "數據不完整"
            }), 400
        
        # 使用數據庫適配器保存激活碼
        success = db_adapter.save_activation_code(activation_code, code_data)
        
        # 同時更新本地JSON文件（向後兼容）
        try:
            bot_data = get_bot_database()
            bot_data['activation_codes'][activation_code] = code_data
            
            # 更新統計
            if 'statistics' not in bot_data:
                bot_data['statistics'] = {}
            if 'activations_generated' not in bot_data['statistics']:
                bot_data['statistics']['activations_generated'] = 0
            
            bot_data['statistics']['activations_generated'] = len(bot_data['activation_codes'])
            
            # 保存到本地JSON文件
            with open(BOT_DATABASE_PATH, 'w', encoding='utf-8') as f:
                json.dump(bot_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"本地JSON保存失敗: {e}")
        
        if success:
            return jsonify({
                "success": True,
                "message": f"激活碼 {activation_code} 同步成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"激活碼 {activation_code} 同步失敗"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"同步錯誤: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🚀 TG旺企業管理系統 - 機器人數據整合版")
    print("=" * 60)
    print("🔗 已整合TG機器人數據:")
    print("   ✅ 機器人訂單數據")
    print("   ✅ 激活碼管理")
    print("   ✅ 用戶採集數據")
    print("   ✅ 實時統計分析")
    print("=" * 60)
    print("📊 數據來源:")
    print(f"   📄 機器人數據庫: {BOT_DATABASE_PATH}")
    print(f"   📁 採集數據目錄: {UPLOAD_DATA_DIR}")
    print("=" * 60)
    print("📌 預設帳號:")
    print(f"   admin/{ADMIN_PASSWORD} (超級管理員)")
    print(f"   manager/{MANAGER_PASSWORD} (業務經理)")
    print(f"   agent/{AGENT_PASSWORD} (代理商)")
    print("=" * 60)
    
    # 獲取端口
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)