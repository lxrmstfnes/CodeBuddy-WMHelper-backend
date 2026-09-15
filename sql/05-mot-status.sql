-- =============================================================
-- MoT 商机闭环：status / done_at（增量，给已有库补列）
-- 数据库: wealth_copilot
-- 新装请走 01-schema.sql（已含这两列）；本脚本只给存量库用
-- =============================================================

USE wealth_copilot;
SET NAMES utf8mb4;

-- 幂等：列已存在则跳过（information_schema 判断）
SET @col_status := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'mot_event' AND COLUMN_NAME = 'status'
);
SET @sql_status := IF(@col_status = 0,
  'ALTER TABLE mot_event ADD COLUMN status VARCHAR(16) DEFAULT ''pending'' COMMENT ''pending待办/done已处理''',
  'SELECT 1');
PREPARE stmt FROM @sql_status; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_done := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'mot_event' AND COLUMN_NAME = 'done_at'
);
SET @sql_done := IF(@col_done = 0,
  'ALTER TABLE mot_event ADD COLUMN done_at DATETIME COMMENT ''处理完成时间''',
  'SELECT 1');
PREPARE stmt FROM @sql_done; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE mot_event SET status = 'pending' WHERE status IS NULL;
-- 演示用：把商机日期拉到今天，保证 MoT「今日」时间线能命中
UPDATE mot_event SET event_date = CURDATE();
