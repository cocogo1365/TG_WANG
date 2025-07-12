#!/usr/bin/env python3
"""
修復上傳邏輯，使用 PostgreSQL 存儲採集數據
"""

# 在 integrated_enterprise_app.py 的第 1650 行附近，替換 api_upload_collection_data 函數

def get_new_upload_collection_data_function():
    return '''
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
'''

# 還需要添加從 PostgreSQL 讀取數據的函數
def get_postgresql_collection_data_function():
    return '''
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
'''

# 修改 get_uploaded_data 函數
def get_modified_get_uploaded_data_function():
    return '''
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
'''

if __name__ == "__main__":
    print("=== PostgreSQL 採集數據存儲修復 ===")
    print("\n1. 替換 api_upload_collection_data 函數（第 1650 行附近）：")
    print("-" * 60)
    print(get_new_upload_collection_data_function())
    print("-" * 60)
    
    print("\n2. 在 get_uploaded_data 函數前添加新函數：")
    print("-" * 60)
    print(get_postgresql_collection_data_function())
    print("-" * 60)
    
    print("\n3. 替換 get_uploaded_data 函數：")
    print("-" * 60)
    print(get_modified_get_uploaded_data_function())
    print("-" * 60)