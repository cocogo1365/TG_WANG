#!/usr/bin/env python3
"""
修復軟體上傳器以包含設備信息和IP位置
這個文件展示了需要在 雲端數據上傳系統.py 中修改的內容
"""

# 在 CloudDataUploader 類的 __init__ 方法中添加：
def get_device_info(self):
    """獲取設備信息"""
    import platform
    return {
        'hostname': platform.node(),
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }

def get_ip_location(self):
    """獲取IP位置信息"""
    try:
        import requests
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'ip': data.get('ip', ''),
                'city': data.get('city', ''),
                'region': data.get('region', ''),
                'country': data.get('country_name', ''),
                'country_code': data.get('country_code', ''),
                'latitude': data.get('latitude', ''),
                'longitude': data.get('longitude', '')
            }
    except:
        pass
    return {}

# 修改 upload_collected_data 方法中的請求數據：
"""
原本的代碼：
response = requests.post(
    f"{self.api_url}/api/upload_software_data",
    json={
        'activation_code': self.activation_code,
        'device_id': self.device_id,
        'data': {
            'collections': [{
                'target_group': collection_info.get('source_group', 'unknown'),
                'collected_count': len(members_data),
                'members': self._serialize_data(members_data),
                'collection_time': datetime.now().isoformat()
            }],
            'status': 'running'
        }
    },
    ...
)

應該改為：
response = requests.post(
    f"{self.api_url}/api/upload_software_data",
    json={
        'activation_code': self.activation_code,
        'device_id': self.device_id,
        'device_info': self.get_device_info(),  # 添加設備信息
        'ip_location': self.get_ip_location(),  # 添加IP位置
        'data': {
            'collections': [{
                'target_group': collection_info.get('source_group', 'unknown'),
                'collected_count': len(members_data),
                'members': self._serialize_data(members_data),
                'collection_time': datetime.now().isoformat()
            }],
            'status': 'running'
        }
    },
    ...
)
"""

print("請將這些修改應用到 C:\\Users\\XX11\\PythonProject6\\TG-旺\\working_release\\雲端數據上傳系統.py")