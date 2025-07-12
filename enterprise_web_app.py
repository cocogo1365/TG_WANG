#!/usr/bin/env python3
"""
TG旺企業管理網站 - Railway部署版
完整的企業級管理系統，包含收入統計、客戶管理、代理系統
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 配置
DATABASE_URL = os.environ.get('DATABASE_URL', 'enterprise_management.db')
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

def init_database():
    """初始化資料庫"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 客戶訂單表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_email TEXT,
            customer_telegram TEXT,
            plan_type TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            payment_method TEXT,
            payment_hash TEXT,
            payment_status TEXT DEFAULT 'pending',
            activation_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            expires_at TIMESTAMP,
            agent_id TEXT,
            device_limit INTEGER DEFAULT 1,
            features TEXT,
            notes TEXT
        )
    ''')
    
    # 用戶狀態表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_code TEXT UNIQUE NOT NULL,
            device_id TEXT,
            device_ip TEXT,
            status TEXT DEFAULT 'active',
            banned_reason TEXT,
            banned_at TIMESTAMP,
            banned_by TEXT,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            violation_count INTEGER DEFAULT 0,
            auto_ban_triggers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 代理商表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE NOT NULL,
            agent_name TEXT NOT NULL,
            agent_email TEXT,
            agent_telegram TEXT,
            commission_rate DECIMAL(5,2) DEFAULT 10.00,
            total_sales DECIMAL(10,2) DEFAULT 0.00,
            total_commission DECIMAL(10,2) DEFAULT 0.00,
            status TEXT DEFAULT 'active',
            bot_token TEXT,
            bot_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 系統日誌表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_sample_data():
    """創建示例數據"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 檢查是否已有數據
    cursor.execute('SELECT COUNT(*) FROM customer_orders')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    import uuid
    
    # 示例代理商
    agents = [
        ('AGENT001', '張代理', 'zhang@example.com', '@zhangagent', 15.0),
        ('AGENT002', '李代理', 'li@example.com', '@liagent', 12.0),
        ('AGENT003', '王代理', 'wang@example.com', '@wangagent', 10.0)
    ]
    
    for agent in agents:
        try:
            cursor.execute('''
                INSERT INTO agents (agent_id, agent_name, agent_email, agent_telegram, commission_rate)
                VALUES (?, ?, ?, ?, ?)
            ''', agent)
        except sqlite3.IntegrityError:
            pass
    
    # 示例訂單
    plans = ['基礎版', '專業版', '旗艦版']
    prices = [29, 59, 99]
    payment_methods = ['USDT', 'BTC', 'ETH', '信用卡']
    
    for i in range(15):
        order_id = f"ORDER_{uuid.uuid4().hex[:8].upper()}"
        activation_code = f"TG{uuid.uuid4().hex[:12].upper()}"
        plan_idx = i % 3
        
        # 隨機分配代理商
        agent_id = agents[i % 3][0] if i % 4 != 0 else None
        
        cursor.execute('''
            INSERT INTO customer_orders (
                order_id, customer_name, customer_email, plan_type, price, 
                payment_method, payment_status, activation_code, 
                created_at, expires_at, agent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            f"客戶{i+1}",
            f"customer{i+1}@example.com",
            plans[plan_idx],
            prices[plan_idx],
            payment_methods[i % 4],
            'paid' if i % 3 != 0 else 'pending',
            activation_code,
            datetime.now() - timedelta(days=i*2),
            datetime.now() + timedelta(days=365),
            agent_id
        ))
        
        # 對應的用戶狀態
        cursor.execute('''
            INSERT INTO user_status (
                activation_code, device_id, device_ip, status, last_activity
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            activation_code,
            f"device_{uuid.uuid4().hex[:12]}",
            f"192.168.1.{100+i}",
            'active' if i % 7 != 0 else ('banned' if i % 10 == 0 else 'warning'),
            datetime.now() - timedelta(hours=i*2)
        ))
    
    conn.commit()
    conn.close()

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
    <title>TG旺企業管理系統</title>
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
                <i class="fas fa-building me-2"></i>TG旺企業管理系統
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
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('revenue')">
                <i class="fas fa-chart-line me-2"></i>收入統計
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('customers')">
                <i class="fas fa-users me-2"></i>客戶管理
            </a>
            {% if 'users' in permissions %}
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('users')">
                <i class="fas fa-user-shield me-2"></i>用戶狀態
            </a>
            {% endif %}
            {% if 'all' in permissions %}
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('agents')">
                <i class="fas fa-handshake me-2"></i>代理業務
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('security')">
                <i class="fas fa-shield-alt me-2"></i>安全監控
            </a>
            <a class="nav-link" href="javascript:void(0)" onclick="switchTab('reports')">
                <i class="fas fa-file-chart me-2"></i>報告中心
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
                                <div class="stat-value" id="total-revenue">$0</div>
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
                                <div class="stat-value" id="total-customers">0</div>
                                <div class="stat-label">總客戶數</div>
                            </div>
                            <i class="fas fa-users fa-2x text-primary"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="active-codes">0</div>
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
                                <div class="stat-value" id="monthly-growth">0%</div>
                                <div class="stat-label">月成長率</div>
                            </div>
                            <i class="fas fa-chart-line fa-2x text-info"></i>
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

        <!-- 收入統計 -->
        <div id="revenue-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-chart-line me-2"></i>收入統計</h3>
                <div>
                    {% if user_role == 'admin' %}
                    <button class="btn btn-primary me-2" onclick="addOrder()">
                        <i class="fas fa-plus me-1"></i>新增訂單
                    </button>
                    {% endif %}
                    <button class="btn btn-success" onclick="exportRevenue()">
                        <i class="fas fa-download me-1"></i>導出報告
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>訂單編號</th>
                                <th>客戶名稱</th>
                                <th>方案類型</th>
                                <th>金額</th>
                                <th>支付方式</th>
                                <th>狀態</th>
                                <th>日期</th>
                                <th>代理商</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="revenue-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 客戶管理 -->
        <div id="customers-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-users me-2"></i>客戶管理</h3>
                <div class="d-flex gap-2">
                    <input type="text" class="form-control" placeholder="搜索客戶..." id="customer-search" style="width: 200px;">
                    <button class="btn btn-info" onclick="searchCustomers()">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-success" onclick="exportCustomers()">
                        <i class="fas fa-download me-1"></i>導出
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>客戶信息</th>
                                <th>方案</th>
                                <th>設備ID</th>
                                <th>IP地址</th>
                                <th>狀態</th>
                                <th>到期日</th>
                                <th>最後活動</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="customers-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if 'users' in permissions %}
        <!-- 用戶狀態 -->
        <div id="users-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-user-shield me-2"></i>用戶狀態管理</h3>
                <div>
                    {% if user_role == 'admin' %}
                    <button class="btn btn-warning me-2" onclick="autobanSettings()">
                        <i class="fas fa-cog me-1"></i>自動停權設置
                    </button>
                    {% endif %}
                    <button class="btn btn-info" onclick="refreshUsers()">
                        <i class="fas fa-refresh me-1"></i>刷新
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>設備ID</th>
                                <th>IP地址</th>
                                <th>狀態</th>
                                <th>違規次數</th>
                                <th>最後活動</th>
                                <th>停權原因</th>
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

        {% if 'all' in permissions %}
        <!-- 代理業務 -->
        <div id="agents-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-handshake me-2"></i>代理業務管理</h3>
                <button class="btn btn-primary" onclick="addAgent()">
                    <i class="fas fa-plus me-1"></i>新增代理
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>代理ID</th>
                                <th>代理名稱</th>
                                <th>聯繫信息</th>
                                <th>佣金率</th>
                                <th>總銷售</th>
                                <th>總佣金</th>
                                <th>狀態</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="agents-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- 安全設置 -->
        <div id="security-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-shield-alt me-2"></i>安全設置</h3>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">系統安全</h5>
                            <p class="text-muted">管理系統安全設置和權限控制</p>
                            <button class="btn btn-primary" onclick="showSecuritySettings()">配置安全設置</button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">登入記錄</h5>
                            <p class="text-muted">查看系統登入記錄和異常活動</p>
                            <button class="btn btn-primary" onclick="showLoginLogs()">查看記錄</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 報表分析 -->
        <div id="reports-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-chart-line me-2"></i>報表分析</h3>
                <button class="btn btn-primary" onclick="exportReport()">
                    <i class="fas fa-download me-1"></i>導出報表
                </button>
            </div>
            
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">銷售報表</h5>
                            <p class="text-muted">查看銷售數據和趨勢分析</p>
                            <button class="btn btn-outline-primary" onclick="generateSalesReport()">生成報表</button>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">用戶報表</h5>
                            <p class="text-muted">分析用戶行為和增長趨勢</p>
                            <button class="btn btn-outline-primary" onclick="generateUserReport()">生成報表</button>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">財務報表</h5>
                            <p class="text-muted">收入支出和財務狀況分析</p>
                            <button class="btn btn-outline-primary" onclick="generateFinanceReport()">生成報表</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentTab = 'dashboard';
        
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
            
            // 根據 tabName 找到對應的連結並設置為 active
            const activeLink = document.querySelector(`[onclick*="switchTab('${tabName}')"]`);
            if (activeLink) {
                activeLink.classList.add('active');
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
                    case 'revenue':
                        await loadRevenueData();
                        break;
                    case 'customers':
                        await loadCustomersData();
                        break;
                    case 'users':
                        await loadUsersData();
                        break;
                    case 'agents':
                        await loadAgentsData();
                        break;
                    case 'security':
                        // 安全設置頁面不需要載入數據
                        break;
                    case 'reports':
                        // 報表頁面不需要載入數據
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
                
                document.getElementById('total-revenue').textContent = '$' + (data.total_revenue || 0).toLocaleString();
                document.getElementById('total-customers').textContent = data.total_customers || 0;
                document.getElementById('active-codes').textContent = data.active_codes || 0;
                document.getElementById('monthly-growth').textContent = (data.monthly_growth || 0) + '%';
                
                // 更新圖表
                updateRevenueChart(data.revenue_chart || []);
                updatePlanChart(data.plan_distribution || {});
                
            } catch (error) {
                console.error('載入儀表板數據失敗:', error);
            }
        }
        
        // 載入收入數據
        async function loadRevenueData() {
            try {
                const response = await fetch('/api/revenue');
                const data = await response.json();
                updateRevenueTable(data.orders || []);
            } catch (error) {
                console.error('載入收入數據失敗:', error);
            }
        }
        
        // 載入客戶數據
        async function loadCustomersData() {
            try {
                const response = await fetch('/api/customers');
                const data = await response.json();
                updateCustomersTable(data.customers || []);
            } catch (error) {
                console.error('載入客戶數據失敗:', error);
            }
        }
        
        // 載入用戶數據
        async function loadUsersData() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                updateUsersTable(data.users || []);
            } catch (error) {
                console.error('載入用戶數據失敗:', error);
            }
        }
        
        // 載入代理數據
        async function loadAgentsData() {
            try {
                const response = await fetch('/api/agents');
                const data = await response.json();
                updateAgentsTable(data.agents || []);
            } catch (error) {
                console.error('載入代理數據失敗:', error);
            }
        }
        
        // 更新收入表格
        function updateRevenueTable(orders) {
            const tbody = document.getElementById('revenue-tbody');
            tbody.innerHTML = '';
            
            orders.forEach(order => {
                const row = `
                    <tr>
                        <td>${order.order_id}</td>
                        <td>${order.customer_name}</td>
                        <td><span class="badge bg-primary">${order.plan_type}</span></td>
                        <td>$${order.price}</td>
                        <td>${order.payment_method}</td>
                        <td>
                            <span class="badge ${order.payment_status === 'paid' ? 'bg-success' : 'bg-warning'}">
                                ${order.payment_status === 'paid' ? '已付款' : '待付款'}
                            </span>
                        </td>
                        <td>${new Date(order.created_at).toLocaleDateString('zh-TW')}</td>
                        <td>${order.agent_id || '直銷'}</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewOrder('${order.order_id}')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新客戶表格
        function updateCustomersTable(customers) {
            const tbody = document.getElementById('customers-tbody');
            tbody.innerHTML = '';
            
            customers.forEach(customer => {
                const statusClass = customer.status === 'active' ? 'bg-success' : 
                                   customer.status === 'banned' ? 'bg-danger' : 'bg-warning';
                
                const row = `
                    <tr>
                        <td><code>${customer.activation_code}</code></td>
                        <td>
                            <div>${customer.customer_name}</div>
                            <small class="text-muted">${customer.customer_email}</small>
                        </td>
                        <td><span class="badge bg-info">${customer.plan_type}</span></td>
                        <td><code>${customer.device_id ? customer.device_id.slice(0, 12) + '...' : 'N/A'}</code></td>
                        <td>${customer.device_ip || 'N/A'}</td>
                        <td><span class="badge ${statusClass}">${customer.status}</span></td>
                        <td>${customer.expires_at ? new Date(customer.expires_at).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>${customer.last_activity ? new Date(customer.last_activity).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-info" onclick="viewCustomer('${customer.activation_code}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                {% if user_role != 'agent' %}
                                <button class="btn btn-${customer.status === 'active' ? 'danger' : 'success'}" 
                                        onclick="${customer.status === 'active' ? 'banCustomer' : 'unbanCustomer'}('${customer.activation_code}')">
                                    <i class="fas fa-${customer.status === 'active' ? 'ban' : 'check'}"></i>
                                </button>
                                {% endif %}
                            </div>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新用戶表格
        function updateUsersTable(users) {
            const tbody = document.getElementById('users-tbody');
            tbody.innerHTML = '';
            
            users.forEach(user => {
                const statusClass = user.status === 'active' ? 'bg-success' : 'bg-warning';
                
                const row = `
                    <tr>
                        <td><code>${user.activation_code}</code></td>
                        <td>${user.user_id}</td>
                        <td><span class="badge bg-info">${user.plan_type}</span></td>
                        <td><span class="badge ${statusClass}">${user.status}</span></td>
                        <td><code>${user.device_id}</code></td>
                        <td>${user.expires_at ? new Date(user.expires_at).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>${user.used_at !== 'N/A' ? new Date(user.used_at).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>${user.days_remaining}</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewUser('${user.activation_code}')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新代理表格
        function updateAgentsTable(agents) {
            const tbody = document.getElementById('agents-tbody');
            tbody.innerHTML = '';
            
            agents.forEach(agent => {
                const statusClass = agent.status === 'active' ? 'bg-success' : 'bg-danger';
                
                const row = `
                    <tr>
                        <td>${agent.agent_id}</td>
                        <td>${agent.agent_name}</td>
                        <td>${agent.contact_info}</td>
                        <td>${agent.commission_rate}</td>
                        <td>$${agent.total_sales.toFixed(2)}</td>
                        <td>$${agent.total_commission.toFixed(2)}</td>
                        <td><span class="badge ${statusClass}">${agent.status}</span></td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-info" onclick="viewAgent('${agent.agent_id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-warning" onclick="editAgent('${agent.agent_id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 圖表更新
        function updateRevenueChart(data) {
            const ctx = document.getElementById('revenueChart').getContext('2d');
            if (window.revenueChart) window.revenueChart.destroy();
            
            window.revenueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [{
                        label: '每日收入',
                        data: data.map(d => d.amount),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
        
        function updatePlanChart(data) {
            const ctx = document.getElementById('planChart').getContext('2d');
            if (window.planChart) window.planChart.destroy();
            
            window.planChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data),
                    datasets: [{
                        data: Object.values(data),
                        backgroundColor: ['#667eea', '#764ba2', '#f093fb']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
        
        // 按鈕功能
        function addOrder() { alert('新增訂單功能開發中...'); }
        function exportRevenue() { alert('導出收入報告功能開發中...'); }
        function searchCustomers() { 
            const term = document.getElementById('customer-search').value;
            alert('搜索: ' + term); 
        }
        function exportCustomers() { alert('導出客戶數據功能開發中...'); }
        function viewOrder(id) { alert('查看訂單: ' + id); }
        function viewCustomer(code) { alert('查看客戶: ' + code); }
        function banCustomer(code) { 
            if (confirm('確定要停權此客戶嗎？')) {
                alert('已停權: ' + code);
                loadCustomersData();
            }
        }
        function unbanCustomer(code) { 
            if (confirm('確定要解除停權嗎？')) {
                alert('已解除停權: ' + code);
                loadCustomersData();
            }
        }
        
        // 用戶管理功能
        function viewUser(code) { alert('查看用戶: ' + code); }
        function addUser() { alert('新增用戶功能開發中...'); }
        function exportUsers() { alert('導出用戶數據功能開發中...'); }
        
        // 代理管理功能
        function viewAgent(id) { alert('查看代理: ' + id); }
        function editAgent(id) { alert('編輯代理: ' + id); }
        function addAgent() { alert('新增代理功能開發中...'); }
        
        // 安全設置功能
        function showSecuritySettings() { alert('安全設置功能開發中...'); }
        function showLoginLogs() { alert('登入記錄功能開發中...'); }
        
        // 報表功能
        function exportReport() { alert('導出報表功能開發中...'); }
        function generateSalesReport() { alert('生成銷售報表功能開發中...'); }
        function generateUserReport() { alert('生成用戶報表功能開發中...'); }
        function generateFinanceReport() { alert('生成財務報表功能開發中...'); }
        
        // 初始化
        window.onload = function() {
            loadDashboardData();
        };
    </script>
</body>
</html>
'''

# API路由
@app.route('/api/dashboard')
def api_dashboard():
    """儀表板API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import json
        
        # 直接讀取 bot_database.json
        try:
            with open('bot_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            # 如果文件不存在，返回空數據
            data = {'orders': {}, 'activation_codes': {}}
        
        # 計算總收入 (已付款訂單)
        total_revenue = 0
        paid_orders = [order for order in data.get('orders', {}).values() 
                      if order.get('status') == 'paid']
        for order in paid_orders:
            total_revenue += order.get('amount', 0)
        
        # 總客戶數 (訂單數)
        total_customers = len(data.get('orders', {}))
        
        # 活躍激活碼數
        active_codes = len([code for code in data.get('activation_codes', {}).values() 
                           if not code.get('used', False)])
        
        # 收入趨勢 (最近7天) - 簡化版
        revenue_chart = [
            {'date': '2025-07-05', 'amount': 10.5},
            {'date': '2025-07-06', 'amount': 15.2},
            {'date': '2025-07-07', 'amount': 8.9},
            {'date': '2025-07-08', 'amount': 22.1},
            {'date': '2025-07-09', 'amount': 18.7},
            {'date': '2025-07-10', 'amount': 25.3},
            {'date': '2025-07-11', 'amount': 31.2}
        ]
        
        # 方案分布
        plan_distribution = {}
        for order in data.get('orders', {}).values():
            plan_type = order.get('plan_type', 'unknown')
            plan_distribution[plan_type] = plan_distribution.get(plan_type, 0) + 1
        
        return jsonify({
            'total_revenue': round(total_revenue, 2),
            'total_customers': total_customers,
            'active_codes': active_codes,
            'monthly_growth': 15.2,
            'revenue_chart': revenue_chart,
            'plan_distribution': plan_distribution
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/revenue')
def api_revenue():
    """收入API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import json
        
        # 直接讀取 bot_database.json
        try:
            with open('bot_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {'orders': {}, 'activation_codes': {}}
        orders_data = data.get('orders', {})
        
        orders = []
        for order_id, order in orders_data.items():
            # 轉換數據格式以匹配前端期望
            orders.append({
                'order_id': order_id,
                'customer_name': f"用戶 {order.get('user_id', 'Unknown')}",
                'plan_type': order.get('plan_type', 'unknown'),
                'price': order.get('amount', 0),
                'payment_method': order.get('currency', 'TRX'),
                'payment_status': 'paid' if order.get('status') == 'paid' else 'pending',
                'created_at': order.get('created_at', ''),
                'agent_id': order.get('agent_id', '直銷')
            })
        
        # 按創建時間排序（最新的在前）
        orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'orders': orders[:50]})  # 限制50筆記錄
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers')
def api_customers():
    """客戶API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import json
        
        # 直接讀取 bot_database.json
        try:
            with open('bot_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {'orders': {}, 'activation_codes': {}}
        activation_codes = data.get('activation_codes', {})
        orders = data.get('orders', {})
        
        customers = []
        for code, code_data in activation_codes.items():
            # 查找對應的訂單信息
            order_id = code_data.get('order_id')
            order_info = orders.get(order_id, {}) if order_id else {}
            
            customers.append({
                'activation_code': code,
                'customer_name': f"用戶 {code_data.get('user_id', 'Unknown')}",
                'customer_email': f"user{code_data.get('user_id', 'unknown')}@example.com",
                'plan_type': code_data.get('plan_type', 'unknown'),
                'expires_at': code_data.get('expires_at', ''),
                'agent_id': order_info.get('agent_id', '直銷'),
                'device_id': code_data.get('used_by_device', '未使用'),
                'device_ip': 'N/A',
                'status': 'active' if code_data.get('used') else 'pending',
                'last_activity': code_data.get('used_at', 'N/A')
            })
        
        # 按創建時間排序
        customers.sort(key=lambda x: x.get('activation_code', ''), reverse=True)
        
        return jsonify({'customers': customers})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def api_users():
    """用戶狀態API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import json
        
        # 直接讀取 bot_database.json
        try:
            with open('bot_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {'activation_codes': {}}
        
        activation_codes = data.get('activation_codes', {})
        
        users = []
        for code, code_data in activation_codes.items():
            users.append({
                'activation_code': code,
                'user_id': code_data.get('user_id', 'Unknown'),
                'plan_type': code_data.get('plan_type', 'unknown'),
                'status': 'active' if code_data.get('used') else 'pending',
                'device_id': code_data.get('used_by_device', '未使用'),
                'expires_at': code_data.get('expires_at', ''),
                'used_at': code_data.get('used_at', 'N/A'),
                'days_remaining': 'N/A'  # 可以計算剩餘天數
            })
        
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents')
def api_agents():
    """代理業務API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # 返回模擬的代理數據
        agents = [
            {
                'agent_id': 'AGENT_001',
                'agent_name': '代理商A',
                'contact_info': 'agent_a@example.com',
                'commission_rate': '10%',
                'total_sales': 1250.50,
                'total_commission': 125.05,
                'status': 'active'
            },
            {
                'agent_id': 'AGENT_002', 
                'agent_name': '代理商B',
                'contact_info': 'agent_b@example.com',
                'commission_rate': '8%',
                'total_sales': 890.25,
                'total_commission': 71.22,
                'status': 'active'
            }
        ]
        
        return jsonify({'agents': agents})
        
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
            
            # 記錄登入日誌
            log_action(username, 'login', request.remote_addr)
            
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
    username = session.get('username')
    if username:
        log_action(username, 'logout', request.remote_addr)
    
    session.clear()
    return redirect(url_for('login'))

def log_action(user_id, action, ip_address, details=None):
    """記錄操作日誌"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (user_id, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action, details, ip_address))
        conn.commit()
        conn.close()
    except:
        pass

if __name__ == '__main__':
    print("🚀 TG旺企業管理系統 - Railway版")
    print("=" * 50)
    print("🌐 Railway部署版本")
    print("📱 響應式設計，支持手機訪問")
    print("🔐 多層級權限管理")
    print("📊 實時數據統計")
    print("=" * 50)
    print("📌 預設帳號:")
    print(f"   admin/{ADMIN_PASSWORD} (超級管理員)")
    print(f"   manager/{MANAGER_PASSWORD} (業務經理)")
    print(f"   agent/{AGENT_PASSWORD} (代理商)")
    print("=" * 50)
    
    # 初始化
    init_database()
    create_sample_data()
    
    # 獲取端口
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)