-- =============================================================
-- 客户数据库 + AI 跟踪 · 增量 Schema（客户数据库与AI跟踪设计.md §1）
-- 数据库: wealth_copilot（幂等脚本,重复执行会先删表重建,仅限开发环境!）
-- 说明: 增量脚本,不动 01-schema.sql 的 9 张表
-- =============================================================

USE wealth_copilot;
SET NAMES utf8mb4;

DROP TABLE IF EXISTS follow_task;
DROP TABLE IF EXISTS customer_event;
DROP TABLE IF EXISTS customer;

-- 设计稿 §1.1 客户主档（持仓 JSON 内嵌，已评审确认）
CREATE TABLE customer (
  id VARCHAR(16) PRIMARY KEY COMMENT '客户ID,如 c001',
  name VARCHAR(32) NOT NULL,
  phone VARCHAR(16),
  age VARCHAR(16) COMMENT '年龄段:"36-50岁"',
  risk_level VARCHAR(4) COMMENT '风险等级 R1-R4',
  aum INT COMMENT '在行总资产(元)',
  tags JSON COMMENT '标签数组:["批发商户","重灵活性"]',
  persona VARCHAR(255) COMMENT '性格/画像一句话备注',
  holdings JSON COMMENT '持仓数组:[{productId,name,amount,buyDate,dueDate,floatPnlPct}]',
  touch_pref VARCHAR(255) COMMENT '触达偏好,如"上午9点/晚8点后接听率高"',
  created_at DATETIME,
  updated_at DATETIME
) DEFAULT CHARSET utf8mb4 COMMENT='客户主档(设计稿§1.1)';

-- 设计稿 §1.2 客户动态流水（沟通记录并入,已评审确认）
CREATE TABLE customer_event (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_id VARCHAR(16) NOT NULL,
  type VARCHAR(16) COMMENT 'maturity到期/buy买入/redeem赎回/transfer大额变动/contact沟通/risk_eval风险测评/alert预警',
  event_time DATETIME COMMENT '事件发生时间',
  title VARCHAR(128) COMMENT '一句话事件:"赎回稳添利50万"',
  payload JSON COMMENT '结构化细节;沟通类(type=contact)存AI抽取结果',
  source VARCHAR(16) COMMENT 'manual手工/ai_extract AI抽取/system系统计算',
  created_at DATETIME,
  INDEX idx_customer_time (customer_id, event_time)
) DEFAULT CHARSET utf8mb4 COMMENT='客户动态流水(设计稿§1.2)';

-- 设计稿 §1.3 跟进待办（闭环载体）
CREATE TABLE follow_task (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_id VARCHAR(16) NOT NULL,
  title VARCHAR(128) COMMENT '如"回访张阿姨确认资金到账"',
  due_time DATETIME,
  status VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/done/cancelled',
  source VARCHAR(16) COMMENT 'ai AI生成/manual人工',
  related_event_id BIGINT COMMENT '来源事件ID(可追溯)',
  ai_suggestion TEXT COMMENT '生成时AI附带的建议话术/策略',
  done_note VARCHAR(255),
  created_at DATETIME,
  updated_at DATETIME,
  INDEX idx_customer_status (customer_id, status),
  INDEX idx_due (due_time, status)
) DEFAULT CHARSET utf8mb4 COMMENT='跟进待办(设计稿§1.3)';
