-- =============================================================
-- 扫码建档 · 增量 Schema（客户自助采集）
-- 给 customer 补所属经理 / 来源 / 画像快照；新建一次性采集码表
-- 幂等：列已存在则跳过；intake_token 可重复执行
-- =============================================================

USE wealth_copilot;
SET NAMES utf8mb4;

-- customer.manager_id
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'customer' AND COLUMN_NAME = 'manager_id') = 0,
  'ALTER TABLE customer ADD COLUMN manager_id VARCHAR(32) DEFAULT ''demo-manager'' COMMENT ''所属理财经理'' AFTER id',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- customer.source: seed存量 / intake扫码 / manual手工
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'customer' AND COLUMN_NAME = 'source') = 0,
  'ALTER TABLE customer ADD COLUMN source VARCHAR(16) DEFAULT ''seed'' COMMENT ''来源:seed/intake/manual'' AFTER touch_pref',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- customer.profile: 诊断画像快照（非正式适当性）
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'customer' AND COLUMN_NAME = 'profile') = 0,
  'ALTER TABLE customer ADD COLUMN profile JSON COMMENT ''AI画像快照(客户自述,非正式测评)'' AFTER source',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE customer SET manager_id = 'demo-manager' WHERE manager_id IS NULL OR manager_id = '';
UPDATE customer SET source = 'seed' WHERE source IS NULL OR source = '';

CREATE TABLE IF NOT EXISTS intake_token (
  token VARCHAR(64) PRIMARY KEY COMMENT '一次性采集码',
  manager_id VARCHAR(32) NOT NULL COMMENT '出示码的理财经理',
  status VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/used/expired/cancelled',
  customer_id VARCHAR(16) COMMENT '提交成功后回写客户ID',
  expire_at DATETIME NOT NULL,
  created_at DATETIME,
  used_at DATETIME,
  INDEX idx_manager_status (manager_id, status)
) DEFAULT CHARSET utf8mb4 COMMENT='扫码建档一次性token';
