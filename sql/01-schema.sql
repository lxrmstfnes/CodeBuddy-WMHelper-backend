-- =============================================================
-- 智能理财经理赋能助手 · 后端数据库 Schema
-- 数据库: OceanBase(MySQL 租户模式,root@test)
-- 依据: BACKEND_SPEC.md §3 数据模型 / §6.4 建表示例
-- 说明: 幂等脚本,重复执行会先删表重建(仅限开发环境!)
-- =============================================================

CREATE DATABASE IF NOT EXISTS wealth_copilot DEFAULT CHARSET utf8mb4;
USE wealth_copilot;
SET NAMES utf8mb4;

DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS company;
DROP TABLE IF EXISTS client_persona;
DROP TABLE IF EXISTS market_report;
DROP TABLE IF EXISTS market_report_card;
DROP TABLE IF EXISTS role_play_script;
DROP TABLE IF EXISTS script_round;
DROP TABLE IF EXISTS forbidden_word;
DROP TABLE IF EXISTS mot_event;

-- §3.1 理财产品
CREATE TABLE product (
  id VARCHAR(16) PRIMARY KEY COMMENT '产品ID,如 p001',
  company VARCHAR(32) NOT NULL COMMENT '理财子公司名称',
  name VARCHAR(64) NOT NULL COMMENT '产品名称',
  tags JSON COMMENT '标签数组:["大行背书","稳健低波"]',
  nature VARCHAR(16) COMMENT '产品性质:公募固收/公募现金管理等',
  sale_type VARCHAR(16) COMMENT '销售类型:代销/自营',
  risk_level VARCHAR(4) COMMENT '风险等级 R1-R4',
  min_amount INT COMMENT '起购金额(元)',
  term VARCHAR(16) COMMENT '期限:"180天"/"1年"/"活期"',
  benchmark_yield VARCHAR(8) COMMENT '业绩比较基准,带%字符串',
  trend JSON COMMENT '近8期收益率数组,前端 Sparkline 用',
  asset_type VARCHAR(128) COMMENT '底层资产文本:"80%纯债 + 20%非标"格式',
  selling_point VARCHAR(255) COMMENT '卖点一句话'
) DEFAULT CHARSET utf8mb4 COMMENT='理财产品(§3.1)';

-- §3.2 理财子公司
CREATE TABLE company (
  id VARCHAR(16) PRIMARY KEY,
  name VARCHAR(32) NOT NULL,
  short VARCHAR(16) COMMENT '简称:工银/杭银/兴银/渝农商',
  slogan VARCHAR(64),
  color VARCHAR(8) COMMENT '前端主题色,如 #1E3A8A'
) DEFAULT CHARSET utf8mb4 COMMENT='理财子公司(§3.2)';

-- §3.3 客群画像
CREATE TABLE client_persona (
  id VARCHAR(16) PRIMARY KEY,
  label VARCHAR(64) NOT NULL COMMENT '客群名称',
  assets VARCHAR(16) COMMENT '资产量级文本:"80万"',
  age VARCHAR(16) COMMENT '年龄段:"36-50岁"',
  pain_point VARCHAR(255),
  golden_line VARCHAR(128) COMMENT '金句',
  quick_prefs JSON COMMENT '偏好标签数组',
  ai_match JSON COMMENT '推荐产品数组(文本)'
) DEFAULT CHARSET utf8mb4 COMMENT='客群画像(§3.3)';

-- §3.4 市场快报(主表)
CREATE TABLE market_report (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_date DATE NOT NULL COMMENT '快报日期',
  golden_sentence VARCHAR(255) COMMENT 'AI 金句(后续升级为大模型每日生成)',
  UNIQUE KEY uk_report_date (report_date)
) DEFAULT CHARSET utf8mb4 COMMENT='市场快报主表(§3.4)';

-- §3.4 市场快报卡片
CREATE TABLE market_report_card (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_date DATE NOT NULL COMMENT '关联快报日期',
  card_no INT NOT NULL COMMENT '前端卡片 id(1/2/3)',
  title VARCHAR(64),
  highlight VARCHAR(32) COMMENT '高亮数字,如 "+70 BP"',
  arrow VARCHAR(8) COMMENT '箭头 emoji,可选',
  sub_text VARCHAR(64),
  color VARCHAR(8),
  show_progress TINYINT DEFAULT 0,
  progress_value INT,
  pulse_dot TINYINT DEFAULT 0 COMMENT '是否脉冲红点',
  sort_no INT DEFAULT 0,
  INDEX idx_report_date (report_date)
) DEFAULT CHARSET utf8mb4 COMMENT='快报卡片(§3.4)';

-- §3.5 对练剧本(主表)
CREATE TABLE role_play_script (
  id VARCHAR(16) PRIMARY KEY,
  title VARCHAR(64),
  difficulty VARCHAR(8) COMMENT '星级难度,如 ★★★☆☆',
  persona VARCHAR(255) COMMENT '客户人设',
  opening TEXT COMMENT '开场白'
) DEFAULT CHARSET utf8mb4 COMMENT='对练剧本(§3.5)';

-- §3.5 剧本轮次(子表)
CREATE TABLE script_round (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  script_id VARCHAR(16) NOT NULL,
  round_no INT NOT NULL COMMENT '轮次序号 0/1/2(与前端 roundIdx 对齐)',
  question VARCHAR(255) COMMENT '该轮客户台词参考方向',
  keywords JSON COMMENT '评分考察关键点数组',
  tips VARCHAR(255) COMMENT '教练提示',
  best_reply TEXT COMMENT '满分话术参考',
  INDEX idx_script (script_id)
) DEFAULT CHARSET utf8mb4 COMMENT='剧本轮次(§3.5)';

-- §3.7 合规违禁词
CREATE TABLE forbidden_word (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  word VARCHAR(32) NOT NULL,
  alternative VARCHAR(255) COMMENT '行内核准替代表述',
  enabled TINYINT DEFAULT 1,
  UNIQUE KEY uk_word (word)
) DEFAULT CHARSET utf8mb4 COMMENT='违禁词库(§3.7)';

-- §3.6 MoT 商机事件
CREATE TABLE mot_event (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_date DATE COMMENT '商机日期(种子数据用 CURDATE(),保证"今日"时间线可见)',
  event_time VARCHAR(8) COMMENT '如 "09:00"',
  type VARCHAR(16) COMMENT 'maturity到期/behavior行为追踪/alert风险预警',
  client_name VARCHAR(32),
  client_tag VARCHAR(64),
  event_title VARCHAR(128),
  detail VARCHAR(255),
  ai_strategy TEXT COMMENT 'AI 跟进策略(后续可改大模型实时生成)',
  generated_script TEXT COMMENT 'AI 生成话术',
  phone VARCHAR(16),
  customer_no VARCHAR(32),
  assets VARCHAR(32),
  risk VARCHAR(32),
  traits VARCHAR(255),
  touch VARCHAR(255),
  status VARCHAR(16) DEFAULT 'pending' COMMENT 'pending待办/done已处理',
  done_at DATETIME COMMENT '处理完成时间',
  result VARCHAR(16) COMMENT 'purchased已购买/intent已意向/informed已了解/follow再跟进/no_intent暂无意向/missed未联系上',
  next_action VARCHAR(16) COMMENT 'crm录入CRM/none无后续'
) DEFAULT CHARSET utf8mb4 COMMENT='MoT 商机事件(§3.6)';
