-- =============================================================
-- 客户数据库 · 种子数据（客户数据库与AI跟踪设计.md §5）
-- 5 个虚拟客户,故事互相咬合;日期全部用 CURDATE()/NOW() 相对偏移,
-- 保证任何时候演示都有"今天到期/今日待办"的数据（沿用 MoT 种子技巧）
-- 幂等: 先清三张表再插
-- =============================================================

USE wealth_copilot;
SET NAMES utf8mb4;

DELETE FROM follow_task;
DELETE FROM customer_event;
DELETE FROM customer;

-- ============ 1. 客户主档 ============
INSERT INTO customer (id, name, phone, age, risk_level, aum, tags, persona, holdings, touch_pref, created_at, updated_at) VALUES
-- c001 王老板：建材批发商,300万存单明天到期（晨报/到期接续主角）
('c001', '王老板', '13866882391', '46-55岁', 'R2', 5200000,
 '["批发商户","重灵活性","存单偏好"]',
 '白手起家建材城批发档口老板，信奉"看得见摸得着"，只买过大额存单，对净值波动敏感',
 CONCAT('[{"productId":"dp300","name":"3年期大额存单","amount":3000000,"buyDate":"2023-09-16","dueDate":"',
        DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d'), '","floatPnlPct":0}]'),
 '白天忙生意，上午9点与晚8点后接听率最高', NOW(), NOW()),
-- c002 张阿姨：退休教师,承诺周五前回访（自动待办主角）
('c002', '张阿姨', '13905712266', '56-65岁', 'R2', 800000,
 '["退休教师","稳健优先","决策周期长"]',
 '退休金理财，极度在意本金安全，购买前要和女儿商量，答应的事一定要兑现',
 '[{"productId":"p001","name":"核心优选鑫尊固收+","amount":200000,"buyDate":"2026-06-10","dueDate":"2026-12-07","floatPnlPct":1.2}]',
 '下午2-4点午睡后精神好，喜欢慢慢聊，忌催促', NOW(), NOW()),
-- c003 李姐：企业财务,持仓浮亏 -4.8%（安抚/预警主角）
('c003', '李姐', '13777889900', '36-45岁', 'R3', 1500000,
 '["企业财务","有理财经验","近期焦虑"]',
 '企业财务主管，懂产品但近期浮亏导致情绪波动，上周已来电咨询两次',
 '[{"productId":"p002","name":"幸福99丰裕添益封闭式","amount":300000,"buyDate":"2026-05-20","dueDate":"2027-05-20","floatPnlPct":-4.8}]',
 '工作时间可接企微消息，午休12-13点勿扰', NOW(), NOW()),
-- c004 陈先生：上月赎回50万转他行（流失预警主角）
('c004', '陈先生', '13612345566', '26-35岁', 'R4', 600000,
 '["互联网从业","高波动承受","价格敏感"]',
 '互联网大厂程序员，习惯货比三家，对他行高收益产品敏感，忠诚度低',
 '[{"productId":"p003","name":"稳添利日盈现金管理","amount":100000,"buyDate":"2026-08-01","dueDate":null,"floatPnlPct":0.4}]',
 '晚上9点后活跃，偏爱线上文字沟通不接电话', NOW(), NOW()),
-- c005 刘阿姨：新客,风险测评下周到期（合规提醒主角）
('c005', '刘阿姨', '13599887744', '46-55岁', 'R1', 300000,
 '["新客户","厅堂流量","测评将过期"]',
 '社区沙龙引流新客，仅做过一次风险测评，尚未购买任何产品',
 '[]',
 '门店周边居民，欢迎到店聊', NOW(), NOW());

-- ============ 2. 客户动态流水（近30天时间线） ============
INSERT INTO customer_event (customer_id, type, event_time, title, payload, source, created_at) VALUES
-- 王老板: 3年前买入存单 → 上周沟通 → 明天到期(系统事件)
('c001', 'buy',      DATE_SUB(NOW(), INTERVAL 30 DAY), '存单进入到期30天窗口', '{"productId":"dp300","amount":3000000}', 'system', NOW()),
('c001', 'contact',  DATE_SUB(NOW(), INTERVAL 6 DAY),  '电话沟通：近期无大额采购计划', '{"channel":"phone","summary":"客户表示近期无进货大单，资金可中期锁定","aiExtract":{"intent":"接续意向正面","promise":null}}', 'ai_extract', NOW()),
('c001', 'maturity', DATE_ADD(NOW(), INTERVAL 1 DAY),  '【300万大额存单明日到期】', '{"productId":"dp300","amount":3000000,"daysLeft":1}', 'system', NOW()),
-- 张阿姨: 买入固收+ → 前天面谈承诺周五前回访
('c002', 'buy',      DATE_SUB(NOW(), INTERVAL 60 DAY), '买入工银核心优选20万', '{"productId":"p001","amount":200000}', 'manual', NOW()),
('c002', 'contact',  DATE_SUB(NOW(), INTERVAL 2 DAY),  '到店面谈：等拆迁款到账再加仓', '{"channel":"store","summary":"拆迁款预计周五前到账，到账后考虑追加30万，约定到账后回访","aiExtract":{"intent":"加仓意向强","promise":"周五前回访确认资金到账"}}', 'ai_extract', NOW()),
-- 李姐: 买入固收+ → 近期回撤预警 → 两次焦虑来电
('c003', 'buy',      DATE_SUB(NOW(), INTERVAL 90 DAY), '买入幸福99丰裕添益30万', '{"productId":"p002","amount":300000}', 'manual', NOW()),
('c003', 'contact',  DATE_SUB(NOW(), INTERVAL 7 DAY),  '来电咨询净值下跌原因', '{"channel":"phone","summary":"客户询问为何浮亏，解释债市调整，情绪稍缓","aiExtract":{"intent":"焦虑求安抚","promise":null}}', 'ai_extract', NOW()),
('c003', 'alert',    DATE_SUB(NOW(), INTERVAL 1 DAY),  '持仓浮亏扩大至-4.8%', '{"productId":"p002","floatPnlPct":-4.8,"threshold":-4}', 'system', NOW()),
-- 陈先生: 上月赎回50万并转出他行
('c004', 'redeem',   DATE_SUB(NOW(), INTERVAL 20 DAY), '赎回某固收产品50万', '{"amount":500000,"reason":"他行专享理财基准高30BP"}', 'manual', NOW()),
('c004', 'transfer', DATE_SUB(NOW(), INTERVAL 19 DAY), '大额资金转出50万（他行）', '{"amount":500000,"direction":"out","bank":"他行"}', 'system', NOW()),
-- 刘阿姨: 新客测评,下周到期
('c005', 'risk_eval', DATE_SUB(NOW(), INTERVAL 350 DAY), '首次风险测评 R1', '{"result":"R1"}', 'manual', NOW()),
('c005', 'risk_eval', DATE_ADD(NOW(), INTERVAL 7 DAY),  '风险测评即将过期(剩余7天)', '{"validDaysLeft":7}', 'system', NOW());

-- ============ 3. 跟进待办 ============
-- 种子的 related_event_id 暂不关联具体事件(运行时由 followup/extract 接口写入并关联)
INSERT INTO follow_task (customer_id, title, due_time, status, source, ai_suggestion, created_at, updated_at) VALUES
-- 张阿姨: 周五回访（今天周二,+3天=周五）
('c002', '回访张阿姨：确认拆迁款到账情况', CONCAT(DATE_ADD(CURDATE(), INTERVAL 3 DAY), ' 14:00:00'), 'pending', 'ai',
 '先问候再提资金，若到账可顺势介绍工银核心优选的历史表现；客户要和女儿商量，别催单', NOW(), NOW()),
-- 王老板: 明天到期,今日触达
('c001', '王老板存单到期前触达：锁定承接方案', CONCAT(CURDATE(), ' 18:00:00'), 'pending', 'system',
 '用"四笔钱"逻辑：100万兴银现金管理保流动性，200万工银核心优选锁中期收益；晚8点后拨打', NOW(), NOW()),
-- 李姐: 浮亏安抚
('c003', '李姐持仓安抚：发送债市解读+约复盘', CONCAT(CURDATE(), ' 17:00:00'), 'pending', 'ai',
 '先共情不辩解，用债市调整是阶段性的口径；附上市场快报卡片，约本周复盘电话', NOW(), NOW());
