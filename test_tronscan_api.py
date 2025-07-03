#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專門測試 TronScan API 連接
"""

import os
import json
import urllib.request
import urllib.parse

def test_tronscan_api():
    """測試 TronScan API 各個端點"""
    
    api_key = os.getenv('TRONGRID_API_KEY')
    if not api_key:
        print("❌ TRONGRID_API_KEY 未設置")
        return False
    
    print(f"🔑 API 密鑰: {api_key[:10]}...")
    print("🌐 測試 TronScan API 連接...")
    
    # 測試各個端點
    endpoints = [
        {
            'name': '區塊查詢',
            'url': 'https://apilist.tronscanapi.com/api/block',
            'method': 'GET'
        },
        {
            'name': '交易查詢',
            'url': 'https://apilist.tronscanapi.com/api/transaction',
            'method': 'GET',
            'params': {
                'limit': 5,
                'address': os.getenv('USDT_ADDRESS', 'TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP'),
                'start': 0
            }
        }
    ]
    
    headers = {
        'TRON-PRO-API-KEY': api_key
    }
    
    success_count = 0
    
    for endpoint in endpoints:
        print(f"\n📡 測試: {endpoint['name']}")
        
        url = endpoint['url']
        if 'params' in endpoint:
            query_string = urllib.parse.urlencode(endpoint['params'])
            url = f"{url}?{query_string}"
        
        print(f"   URL: {url}")
        
        try:
            req = urllib.request.Request(url, headers=headers, method=endpoint['method'])
            
            with urllib.request.urlopen(req, timeout=15) as response:
                status_code = response.getcode()
                response_data = response.read()
                
                print(f"   狀態: {status_code}")
                
                if status_code == 200:
                    try:
                        data = json.loads(response_data.decode('utf-8'))
                        
                        if endpoint['name'] == '區塊查詢':
                            if isinstance(data, list) and len(data) > 0:
                                block_num = data[0].get('number', 0)
                                print(f"   ✅ 成功獲取區塊: {block_num}")
                                success_count += 1
                            elif isinstance(data, dict) and 'number' in data:
                                print(f"   ✅ 成功獲取區塊: {data['number']}")
                                success_count += 1
                            else:
                                print(f"   ⚠️ 異常響應格式: {type(data)}")
                                print(f"   響應內容: {str(data)[:200]}")
                        
                        elif endpoint['name'] == '交易查詢':
                            if 'data' in data:
                                transactions = data['data']
                                print(f"   ✅ 成功獲取 {len(transactions)} 個交易")
                                success_count += 1
                                
                                # 顯示交易詳情
                                for i, tx in enumerate(transactions[:2]):
                                    print(f"     交易 {i+1}: {tx.get('hash', '未知')[:16]}...")
                                    print(f"     類型: {tx.get('contractType', '未知')}")
                                    print(f"     金額: {tx.get('amount', 0)}")
                            else:
                                print(f"   ⚠️ 無交易數據: {str(data)[:200]}")
                        
                    except json.JSONDecodeError:
                        print(f"   ❌ JSON 解析失敗")
                        print(f"   原始響應: {response_data.decode('utf-8')[:200]}")
                
                elif status_code == 403:
                    print(f"   ❌ API 密鑰無效或權限不足")
                elif status_code == 429:
                    print(f"   ❌ API 請求頻率限制")
                else:
                    print(f"   ❌ 請求失敗: {status_code}")
                    print(f"   錯誤內容: {response_data.decode('utf-8')[:200]}")
                    
        except urllib.error.HTTPError as e:
            print(f"   ❌ HTTP 錯誤: {e.code}")
            try:
                error_data = e.read().decode('utf-8')
                print(f"   錯誤詳情: {error_data[:200]}")
            except:
                pass
        except Exception as e:
            print(f"   ❌ 請求異常: {e}")
    
    print(f"\n🏁 測試完成: {success_count}/{len(endpoints)} 個端點成功")
    
    if success_count == len(endpoints):
        print("✅ 所有 API 端點正常工作！")
        return True
    else:
        print("❌ 部分 API 端點有問題")
        return False

if __name__ == "__main__":
    print("🚀 TronScan API 專項測試")
    print("="*50)
    
    # 檢查環境變量
    api_key = os.getenv('TRONGRID_API_KEY')
    address = os.getenv('USDT_ADDRESS')
    
    print(f"API Key: {'已設置' if api_key else '未設置'}")
    print(f"地址: {address if address else '未設置'}")
    
    print("="*50)
    
    success = test_tronscan_api()
    
    print("="*50)
    if success:
        print("🎉 API 配置完全正確！")
        print("現在機器人的 API 調用應該正常工作")
    else:
        print("🔧 需要檢查 API 密鑰或網絡連接")