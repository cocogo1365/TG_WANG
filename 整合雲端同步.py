#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合雲端同步到TG機器人
在main.py的第239行後添加以下代碼
"""

# 在 TGMarketingBot.__init__ 方法中添加：
"""
        try:
            self.activation_manager = ActivationCodeManager()
            # 添加雲端同步功能
            from 雲端同步機器人 import CloudSyncManager
            self.cloud_sync = CloudSyncManager()
            logger.info("✅ 雲端同步管理器已初始化")
        except Exception as e:
            logger.error(f"❌ 激活碼管理器初始化失敗: {e}")
            raise
"""

# 修改生成激活碼的方法，在激活碼生成後自動同步到雲端
# 找到所有調用 self.activation_manager.generate_activation_code 的地方
# 在生成激活碼後添加同步代碼：

"""
# 示例：在處理試用申請時
activation_code = self.activation_manager.generate_activation_code(
    plan_type='trial',
    days=2,
    user_id=user_id
)

# 添加雲端同步
code_data = {
    'activation_code': activation_code,
    'plan_type': 'trial',
    'user_id': user_id,
    'order_id': None,
    'days': 2,
    'created_at': datetime.now().isoformat(),
    'expires_at': (datetime.now() + timedelta(days=2)).isoformat(),
    'used': False,
    'used_at': None,
    'used_by_device': None
}

# 同步到雲端
if hasattr(self, 'cloud_sync'):
    self.cloud_sync.sync_activation_code_to_cloud(activation_code, code_data)
"""