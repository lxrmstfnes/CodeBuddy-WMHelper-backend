-- 话术库（群发素材）
USE wealth_copilot;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS script_item (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  manager_id VARCHAR(32) DEFAULT 'demo-manager',
  title VARCHAR(64) NOT NULL,
  category VARCHAR(16) DEFAULT 'sales' COMMENT 'season季节问候/sales销售/care关怀/personal个人',
  body TEXT NOT NULL COMMENT '可用 {name} {persona} 占位',
  customer_id VARCHAR(16) COMMENT '个人话术绑定的客户，可空',
  source VARCHAR(16) DEFAULT 'manual' COMMENT 'manual/ai_diagnose/seed',
  created_at DATETIME,
  INDEX idx_manager_cat (manager_id, category),
  INDEX idx_customer (customer_id)
) DEFAULT CHARSET utf8mb4 COMMENT='理财经理话术库';

DELETE FROM script_item WHERE source = 'seed';

INSERT INTO script_item (manager_id, title, category, body, customer_id, source, created_at) VALUES
('demo-manager', '中秋节问候', 'season',
 '{name}中秋安康！月圆人团圆，也提醒您行里的理财持仓我一直帮您盯着。节后如果手头有闲钱，我给您准备了几款稳健的接续方案，您方便时回我一句就行。',
 NULL, 'seed', NOW()),
('demo-manager', '国庆出行关怀', 'care',
 '{name}国庆出行注意安全。假期资金用着用不到都没关系，现金类产品随用随取，回来我再帮您看看要不要做中期配置。',
 NULL, 'seed', NOW()),
('demo-manager', '降息后存单承接', 'sales',
 '{name}，最近又降息了。您这类资金如果还放着等，利息会越来越薄。我按您求稳的习惯挑了两款替代方案，不催单，您先看哪款更合适，我们再细聊。',
 NULL, 'seed', NOW()),
('demo-manager', '市场波动安抚', 'care',
 '{name}看到账户有点波动别慌，这是债市阶段性调整，不是产品出了问题。您的这笔钱期限还没到，把期限拿满，票息大概率能覆盖这点回撤。有疑问随时回我。',
 NULL, 'seed', NOW()),
('demo-manager', '王老板·存单到期破冰', 'personal',
 '王总中秋好！您那笔300万存单窗口期到了。按您进货要灵活的习惯，我还是那句「四笔钱」：100万放现金管理随时取，200万锁中期稳健。今晚8点后方便接个电话吗？',
 'c001', 'seed', NOW()),
('demo-manager', '张阿姨·稳健加仓问候', 'personal',
 '张阿姨您好，先不谈产品。上次说拆迁款到账后咱们再看，我按您求稳、要和女儿商量的节奏，只准备了一份工银固收+的历史表现给您带回去看，绝不催您。',
 'c002', 'seed', NOW()),
('demo-manager', '李姐·浮亏安抚', 'personal',
 '李姐，看到幸福99这几天绿了，先别急着赎回。您懂产品，这次是债市调整不是基本面坏了。今晚我发一份市场快报给您，本周找10分钟复盘一下就好。',
 'c003', 'seed', NOW()),
('demo-manager', '陈先生·流失挽回', 'personal',
 '陈哥，上次转走的那笔我没再追着问。这周同业价差收窄了，我按您习惯整理了一页对比（含流动性），您晚上有空扫一眼，觉得没优势咱们就算了。',
 'c004', 'seed', NOW()),
('demo-manager', '刘阿姨·新客测评提醒', 'personal',
 '刘阿姨，社区沙龙认识您挺高兴。风险测评下周就到期了，这是监管要求，做完才能帮您挑合适的产品。您哪天路过网点，我给您预留10分钟。',
 'c005', 'seed', NOW());
