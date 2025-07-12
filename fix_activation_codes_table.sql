-- 修復 activation_codes 表：添加停權相關欄位
-- 日期：2025-07-12

-- 檢查現有欄位
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'activation_codes'
ORDER BY ordinal_position;

-- 添加缺少的欄位（如果不存在）
ALTER TABLE activation_codes 
ADD COLUMN IF NOT EXISTS disabled BOOLEAN DEFAULT FALSE;

ALTER TABLE activation_codes 
ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMP;

ALTER TABLE activation_codes 
ADD COLUMN IF NOT EXISTS disabled_by VARCHAR(100);

ALTER TABLE activation_codes 
ADD COLUMN IF NOT EXISTS disabled_reason TEXT;

-- 創建索引以提高查詢性能
CREATE INDEX IF NOT EXISTS idx_activation_codes_disabled 
ON activation_codes(disabled);

-- 驗證欄位已添加
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'activation_codes'
AND column_name IN ('disabled', 'disabled_at', 'disabled_by', 'disabled_reason')
ORDER BY ordinal_position;

-- 查看更新後的表結構
\d activation_codes