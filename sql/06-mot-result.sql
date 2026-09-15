-- =============================================================
-- MoT 跟进结论 / 后续动作（增量，给已有库补列）
-- result: purchased/intent/informed/follow/no_intent/missed
-- next_action: crm/none
-- =============================================================

USE wealth_copilot;
SET NAMES utf8mb4;

SET @col_result := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'mot_event' AND COLUMN_NAME = 'result'
);
SET @sql_result := IF(@col_result = 0,
  'ALTER TABLE mot_event ADD COLUMN result VARCHAR(16) COMMENT ''purchased已购买/intent已意向/informed已了解/follow再跟进/no_intent暂无意向/missed未联系上''',
  'SELECT 1');
PREPARE stmt FROM @sql_result; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_next := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'wealth_copilot' AND TABLE_NAME = 'mot_event' AND COLUMN_NAME = 'next_action'
);
SET @sql_next := IF(@col_next = 0,
  'ALTER TABLE mot_event ADD COLUMN next_action VARCHAR(16) COMMENT ''crm录入CRM/none无后续''',
  'SELECT 1');
PREPARE stmt FROM @sql_next; EXECUTE stmt; DEALLOCATE PREPARE stmt;
