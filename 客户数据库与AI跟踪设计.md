# 客户数据库 + AI 跟踪 · 设计稿（待评审）

> 版本：v0.1 评审稿 · 2026-09-15
> 定位：POC 比赛专用，**不是**全量 CRM。目标是把系统从"无状态演示"升级为"数据飞轮"。
> 风格约定：与 `sql/01-schema.sql` / `app/models.py` 保持一致（snake_case 建表 + `to_dict()` 转 camelCase）。

---

## 0. 背景与目标

### 现状短板（为什么做）
| 模块 | 现状 | 问题 |
|---|---|---|
| 跟进助手 | 语音 → AI 抽取 CRM 记录 | **抽取完不落库**，关页面就没 |
| MoT 商机页 | 事件是种子数据写死 | 不是从客户真实变化算出来的 |
| 客群诊断 | persona 是"群体画像" | 没有"具体客户"载体，诊断结果无处挂靠 |

### 目标：数据飞轮
```
客户变化入库 → AI 洞察（解读+建议+话术）→ 合规拦截 → 触达/跟进 → 结果回写 → 再洞察
```

### 非目标（范围控制，防膨胀）
- 不做权限/多角色体系（假定单一理财经理视角）
- 不做真实客户隐私数据（全部虚拟客户，答辩时主动声明个保法合规设计）
- 不做持仓子表（holdings 用 JSON 内嵌——✅ 已评审确认，POC 规模足够）

---

## 1. 数据模型（新增 3 张表）

### 1.1 customer 客户主档
```sql
CREATE TABLE customer (
  id VARCHAR(16) PRIMARY KEY COMMENT '客户ID,如 c001',
  name VARCHAR(32) NOT NULL,
  phone VARCHAR(16),
  age VARCHAR(16) COMMENT '年龄段:"36-50岁"',
  risk_level VARCHAR(4) COMMENT '风险等级 R1-R4',
  aum INT COMMENT '在行总资产(元)',
  tags JSON COMMENT '标签数组:["批发商户","重灵活性"]',
  persona VARCHAR(255) COMMENT '性格/画像一句话备注',
  holdings JSON COMMENT '持仓数组:[{productId,name,amount,buyDate,dueDate,benchmarkYield}]',
  touch_pref VARCHAR(255) COMMENT '触达偏好,如"上午9点/晚8点后接听率高"',
  created_at DATETIME,
  updated_at DATETIME
) DEFAULT CHARSET utf8mb4 COMMENT='客户主档';
```

### 1.2 customer_event 客户动态流水（核心表：所有"变化"都进这条流）
```sql
CREATE TABLE customer_event (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_id VARCHAR(16) NOT NULL,
  type VARCHAR(16) COMMENT 'maturity到期/buy买入/redeem赎回/transfer大额变动/contact沟通/risk_eval风险测评/alert预警',
  event_time DATETIME COMMENT '事件发生时间',
  title VARCHAR(128) COMMENT '一句话事件:"赎回稳添利50万"',
  payload JSON COMMENT '结构化细节:{productId,amount,before,after,...};沟通类存AI抽取结果',
  source VARCHAR(16) COMMENT 'manual手工/ai_extract AI抽取/system系统计算',
  created_at DATETIME,
  INDEX idx_customer_time (customer_id, event_time)
) DEFAULT CHARSET utf8mb4 COMMENT='客户动态流水(含沟通记录)';
```
> 设计要点：**沟通记录不单独建表**，作为 `type='contact'` 进事件流——客户详情页的时间线天然就是"资产变化 + 沟通历史"的统一视图（对应痛点 2）。

### 1.3 follow_task 跟进待办
```sql
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
) DEFAULT CHARSET utf8mb4 COMMENT='跟进待办(闭环载体)';
```

---

## 2. API 清单

统一响应 `{ "code": 0, "message": "ok", "data": {...} }`，沿用现有规范。

### 2.1 数据类（新 `app/routers/customer.py`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/customers` | 客户列表，每条带 `pendingTasks` 待办数、`nearMaturity` 7日内到期标记（列表页徽标用） |
| GET | `/api/customers/{id}` | 客户详情：主档 + 事件时间线（倒序 20 条）+ 未完成任务 |
| POST | `/api/customers/{id}/events` | 手工录入动态（赎回/买入/大额变动），body: `{type, title, payload, eventTime?}` |
| GET | `/api/customers/{id}/tasks` | 该客户待办列表 |
| POST | `/api/tasks/{id}/done` | 完成待办，body: `{doneNote?}` |

### 2.2 AI 类（`app/routers/ai.py` 扩展，全部带 rules 兜底）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ai/followup/extract` | **改造现有端点**：入参加 `customerId`；抽取后 ① 写 `customer_event(type=contact)` ② 解析承诺事项自动生成 `follow_task`。返回 `{record, tasksCreated}` |
| POST | `/api/ai/customers/{id}/insight` | **变动即洞察**：读最近 10 条事件 + 主档 → `{summary 变化解读, risk 风险判断, suggestion 建议动作, script 参考话术}` |
| POST | `/api/ai/briefing` | 【**P2 待定**】经营晨报：系统先算出候选（7日内到期、今日待办、近期赎回/浮亏）→ LLM 生成 → `{date, items: [...], summary}` |

---

## 3. LLM 契约设计（关键原则）

**原则：数字由系统算，LLM 只做语言工作。**（反幻觉核心设计，答辩可讲）
到期天数、浮亏金额、待办数量全部后端预计算进 prompt；LLM 只负责解读、建议、话术。

### 3.1 followup/extract（改造）
- 输入：`{customerId, text（语音转写原文）}`
- 在原 CRM 抽取契约上增加：`promises: [{content, dueDate}]`（"周五前回访" → `dueDate` 推算为具体日期）
- 输出落库：1 条 contact 事件 + N 条 pending 任务；返回 `{record, tasksCreated: [...]}`

### 3.2 insight（变动即洞察）
- 输入（系统组装）：客户主档 + 最近 10 条事件 + **本次触发事件**
- 输出契约：
```json
{
  "summary": "近30天资金净流出80万，流向疑似他行",
  "risk": "medium",
  "suggestion": "今日内电话回访，先共情再探资金用途",
  "script": "王总您好，注意到您上周有笔资金调动……"
}
```
- `risk` 枚举 `low/medium/high`，前端配色用

### 3.3 briefing（经营晨报）【P2 待定，本期不实现】
- 输入（系统预计算候选集）：`{maturities: [...], dueTasks: [...], recentRedeems: [...]}`
- 输出：`items[]` 每条 `{customerId, name, reason, suggestion, script}` + 一句 `summary` 晨报导语
- 候选为空时直接返回"今日无紧急事项"，不调用 LLM（省钱且快）

---

## 4. 前端改动

| 页面 | 改动 |
|---|---|
| **新：客户列表页** `pages/customers/customers` | 头像+姓名+标签+AUM，角标显示待办数/到期提醒；顶部"AI 晨报"入口按钮 |
| **新：客户详情页** `pages/customer-detail/customer-detail` | 三段：档案卡（主档+持仓）→ **统一动态时间线**（资产变化+沟通记录混排）→ AI 洞察卡（risk 配色）+ 待办列表（可勾选完成） |
| 跟进助手 `pages/assistant` | 抽取前先选客户；结果页展示"✅ 已入客户档案 + 📋 自动生成 N 项待办" |
| MoT 页 `pages/mot` | 数据源从种子改为 `customer_event` + holdings 到期日实时计算（接口失败回退种子，兜底原则不变） |
| `app.json` | 注册 2 个新页面 + **tabBar 新增「客户」tab**（✅ 已评审确认：入口放底部） |

---

## 5. 种子数据（5 个虚拟客户，故事互相咬合）

| 客户 | 设定 | 演示用途 |
|---|---|---|
| c001 王老板 | 建材批发商，AUM 500W，**300W 存单明天到期**（与现有 MoT 种子呼应） | 晨报"到期接续"头条 |
| c002 张阿姨 | 退休教师，R2，**上周沟通说"周五前资金到账再约"** | 跟进助手说完自动生成周五待办 |
| c003 李姐 | 企业财务，持有权益类基金，**近7日浮亏 -4.8%** | 晨报"持仓安抚"+ insight 预警 |
| c004 陈先生 | 互联网从业，R4，上月赎回 50W 转他行 | insight"流失风险"演示 |
| c005 刘阿姨 | 新客，风险测评**下周到期** | 晨报"测评过期"合规提醒 |

每人 3~6 条事件时间线（近 30 天），holding 的 dueDate 用 `CURDATE()` 偏移写法保证**任何时候演示晨报都有"今天到期"的数据**（沿用 MoT 种子的老技巧）。

---

## 6. 兼容与兜底（原则不变）

- 前端"接口优先、mock 兜底"：后端挂了一切照旧可演示
- 每个新 AI 端点在 `rules.py` 配规则兜底（insight 给模板化解读，briefing 按候选直接拼装）
- prompt 全部进 `prompts.py`，契约校验进 `normalize.py`，与现有 AI 链路同构

---

## 7. 分期实施

| 期 | 内容 | 预估 |
|---|---|---|
| **P0**（第1天） | 3 表 + 种子 + 客户 CRUD/详情 API + followup 落库改造 + 前端客户列表/详情页 | 1 天 |
| **P1**（第2天） | insight 变动洞察 + 待办闭环 UI + MoT 实时化 | 1 天 |
| **P2**（待定/可选） | briefing 经营晨报（暂缓，见 §8）；企微客户群发打通（推送结果回写 event 流） | 视决策/企微进度 |

---

## 8. 评审决策记录（2026-09-15 已评审）

1. ✅ **持仓 JSON 内嵌**在主档，不建子表
2. ✅ **沟通记录并入 `customer_event`** 事件流（type=contact），不单独建表
3. ⏸️ **晨报整体暂缓**（含"系统预计算数字、LLM 只写解读"的反幻觉设计），移至 P2 待定——该设计的作用是：到期金额、浮亏点数等数字由后端 SQL 算死，LLM 只负责组织语言，杜绝 AI 编造数字
4. ✅ **客户模块入口放底部 tabBar**，新增「客户」tab（非首页快捷入口）
