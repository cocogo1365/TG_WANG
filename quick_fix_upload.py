#!/usr/bin/env python3
"""
快速修復：添加更多日誌來追蹤上傳問題
"""

# 在integrated_enterprise_app.py的相應位置添加以下日誌

# 1. 在get_uploaded_data函數添加日誌
def get_uploaded_data_with_logging():
    """獲取上傳的採集數據（帶日誌）"""
    uploaded_data = []
    
    try:
        upload_dir = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
        print(f"[DEBUG] 檢查上傳目錄: {upload_dir}")
        
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            print(f"[DEBUG] 找到 {len(files)} 個文件")
            
            json_files = [f for f in files if f.endswith('.json')]
            print(f"[DEBUG] 其中 {len(json_files)} 個JSON文件")
            
            for filename in json_files:
                filepath = os.path.join(upload_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        uploaded_data.append(data)
                        print(f"[DEBUG] 成功讀取: {filename}")
                except Exception as e:
                    print(f"[ERROR] 讀取失敗 {filename}: {e}")
        else:
            print(f"[ERROR] 上傳目錄不存在: {upload_dir}")
            # 嘗試創建目錄
            try:
                os.makedirs(upload_dir, exist_ok=True)
                print(f"[INFO] 已創建上傳目錄: {upload_dir}")
            except Exception as e:
                print(f"[ERROR] 創建目錄失敗: {e}")
                
    except Exception as e:
        print(f"[ERROR] 讀取上傳目錄失敗: {e}")
    
    print(f"[DEBUG] 總共載入 {len(uploaded_data)} 個數據文件")
    return uploaded_data

# 2. 在上傳API添加詳細日誌
@app.route('/api/upload_collection_data', methods=['POST'])
def api_upload_collection_data_with_logging():
    """接收採集數據上傳API（帶詳細日誌）"""
    print(f"[API] 收到上傳請求: {request.method} {request.path}")
    print(f"[API] 請求來源: {request.remote_addr}")
    print(f"[API] User-Agent: {request.headers.get('User-Agent')}")
    print(f"[API] Content-Type: {request.headers.get('Content-Type')}")
    
    try:
        data = request.get_json()
        print(f"[API] 請求數據鍵: {list(data.keys()) if data else 'None'}")
        
        activation_code = data.get('activation_code')
        print(f"[API] 激活碼: {activation_code}")
        
        members_data = data.get('members', [])
        print(f"[API] 成員數量: {len(members_data)}")
        
        # ... 處理邏輯 ...
        
        # 保存前日誌
        upload_dir = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
        filename = f"collection_{activation_code}_{int(datetime.now().timestamp())}.json"
        filepath = os.path.join(upload_dir, filename)
        
        print(f"[API] 準備保存到: {filepath}")
        
        # 保存後確認
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"[API] 文件保存成功，大小: {file_size} bytes")
        else:
            print(f"[API] 警告：文件保存後不存在！")
            
        return jsonify({
            'success': True,
            'message': f'成功上傳 {len(members_data)} 個成員數據',
            'debug': {
                'file': filename,
                'path': filepath,
                'exists': os.path.exists(filepath)
            }
        })
        
    except Exception as e:
        print(f"[API ERROR] 上傳失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# 3. 在軟件數據上傳API也添加日誌
@app.route('/api/upload_software_data', methods=['POST'])
def api_upload_software_data_with_logging():
    print(f"[SOFTWARE API] 收到軟件上傳請求")
    # ... 類似的日誌邏輯

# 4. 創建測試端點
@app.route('/api/test_upload_dir')
def test_upload_dir():
    """測試上傳目錄狀態"""
    upload_dir = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
    
    result = {
        'upload_dir': upload_dir,
        'exists': os.path.exists(upload_dir),
        'is_dir': os.path.isdir(upload_dir) if os.path.exists(upload_dir) else False,
        'writable': os.access(upload_dir, os.W_OK) if os.path.exists(upload_dir) else False,
        'files': []
    }
    
    if os.path.exists(upload_dir) and os.path.isdir(upload_dir):
        try:
            files = os.listdir(upload_dir)
            result['files'] = [
                {
                    'name': f,
                    'size': os.path.getsize(os.path.join(upload_dir, f)),
                    'modified': datetime.fromtimestamp(os.path.getmtime(os.path.join(upload_dir, f))).isoformat()
                }
                for f in files[:10]  # 只顯示前10個
            ]
        except Exception as e:
            result['error'] = str(e)
    
    return jsonify(result)