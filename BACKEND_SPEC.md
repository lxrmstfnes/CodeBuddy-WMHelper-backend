# 后端开发交接文档（SOFABoot）

> 本文档是「智能理财经理赋能助手」微信小程序前端项目的完整归纳，供新建 SOFABoot 后端项目开发使用。
> 读完本文档即可明确：要建哪些表、暴露哪些接口、AI 能力的输入输出契约、以及前端需要配合改造的点。
>
> ⚠️ 当前所有业务数据均为虚构演示数据，不构成任何投资建议。

---

## 1. 项目背景

- **定位**：面向县域农商行一线理财经理的展业赋能工具（微信小程序）
- **前端现状**：微信原生小程序（无框架、无 npm 依赖、无构建步骤），5 个页面
- **数据现状**：全部 mock 在前端 `utils/mock.js` 和 `pages/mot/mot.js` 内
- **AI 现状**：对练道场已接入 DeepSeek 大模型（`deepseek-flash`），但是**前端直连**（Key 在前端 `utils/config.js`，仅适合开发调试）

### ⚠️ 最重要的安全事项

**DeepSeek API Key 当前在前端代码里，生产环境必须迁移到后端。** 后端的核心职责之一就是作为大模型调用的代理网关：前端只调自己的后端，Key 存放在服务端配置（application.yml / 配置中心），永不下发。

---

## 2. 前端页面与功能清单

| 页面 | 路径 | 功能 | 数据/AI 依赖 |
| --- | --- | --- | --- |
| 工作台首页 | `pages/home/` | 促单指标快报、AI 金句、产品库（公司筛选/Sparkline 净值/详情抽屉/勾选对比）、AI 穿透点评 | marketReport、products、companies；金句和点评当前是假 AI |
| MoT 关键时刻 | `pages/mot/` | 每日商机时间线（到期/行为/预警三类）、AI 策略与话术、客户画像抽屉 | motEvents（⚠️ 定义在页面 JS 里，不在 mock.js） |
| AI 客户诊断 | `pages/client/` | 画像快填表单 → 雷达图/配置环形图/TOP3 产品匹配/三场景大白话话术 | diagnoseClient()（本地规则引擎，可升级为 AI） |
| 穿透式 PK 台 | `pages/compare/` | 双产品对比、雷达形变、穿透参数表、AI 投顾建议 | utils/pk.js（独立产品数据 PRODUCTS，与 mock.js 不同步） |
| 对练道场 | `pages/training/` | 5 个剧本 3 轮攻防、违禁词实时拦截、AI 逐轮评分、AI 生成客户追问、AI 总结建议 | rolePlayScripts、complianceCheck()；评分/追问/总结已接真实 DeepSeek |

---

## 3. 核心数据模型（建表 / DTO 依据）

### 3.1 Product 理财产品

```json
{
  "id": "p001",
  "company": "工银理财",
  "name": "核心优选鑫尊固收+",
  "tags": ["大行背书", "稳健低波"],
  "nature": "公募固收",
  "saleType": "代销",
  "riskLevel": "R2",
  "minAmount": 10000,
  "term": "180天",
  "benchmarkYield": "3.15%",
  "trend": [2.55, 2.62, 2.58, 2.70, 2.66, 2.78, 2.83, 2.90],
  "assetType": "80%纯债 + 20%非标",
  "sellingPoint": "宇宙行金字招牌，替代大额存单首选，适合首单破冰。"
}
```

字段说明：`riskLevel` 取值 R1-R4；`term` 为字符串（"180天"/"1年"/"活期"）；`benchmarkYield` 带 % 的字符串；`trend` 是近 8 期收益率数组（前端画 Sparkline）；`assetType` 是"xx%资产 + yy%资产"格式文本，前端用正则 `/(\d+)%\s*([^+\d][^+]*)/g` 解析成穿透进度条——**后端若结构化存储（资产明细子表），需保留该文本的生成逻辑或下发明细数组**。

### 3.2 Company 理财子公司

```json
{ "id": "icbc", "name": "工银理财", "short": "工银", "slogan": "大行背书，稳健低波", "color": "#1E3A8A" }
```

共 4 家：工银/杭银/兴银/渝农商。`color` 是前端主题色，可直接存库下发。

### 3.3 ClientPersona 客群画像

```json
{
  "id": "c001",
  "label": "县域个体工商户/批发商",
  "assets": "80万",
  "age": "36-50岁",
  "painPoint": "资金周转要求高，随时要进货，看不上活期利息，又怕亏损。",
  "goldenLine": "先解决资金灵活性，再谈收益",
  "quickPrefs": ["流动性优先", "分散配置"],
  "aiMatch": ["p003(兴银现金管理)"]
}
```

共 3 类（个体户/保守储户/新农人）。前端"一键填充"依赖 `assets` 到表单选项的映射（80万→50-100万，50万/30万→10-50万）。

### 3.4 MarketReport 市场快报

```json
{
  "date": "2026-09-04",
  "cards": [
    { "id": 1, "title": "3年期定存 vs 理财", "highlight": "+70 BP", "arrow": "⬆️", "subText": "2.15% / 2.85%", "color": "#F87171", "showProgress": false },
    { "id": 2, "title": "杭银幸福99额度", "highlight": "剩余 12%", "subText": "额度告急", "color": "#F59E0B", "showProgress": true, "progressValue": 88, "pulseDot": true }
  ],
  "goldenSentence": "把合适的产品放到合适的客户手里——县域的钱更怕亏，稳字当头才是长久生意。"
}
```

`goldenSentence` 计划升级为由大模型基于 cards 数据每日生成。

### 3.5 RolePlayScript 对练剧本（主表 + 轮次子表）

```json
{
  "id": "s01",
  "title": "只认保本的阿姨",
  "difficulty": "★★★☆☆",
  "persona": "62岁退休阿姨，认为\"理财就是存款\"，听说理财会亏钱后非常抗拒。",
  "opening": "小姑娘，你们这个理财产品是不是会亏本金的？……",
  "rounds": [
    {
      "question": "客户表示\"只存定期，理财会亏本金\"",
      "keywords": ["净值", "存款", "保障", "历史", "回撤", "稳", "存款保险"],
      "tips": "先认同\"求稳\"心理，再用R2产品历史正收益数据对比存款利率下行的事实，切忌否定客户。",
      "bestReply": "阿姨您这个想法特别对……"
    }
  ]
}
```

共 5 个剧本，每个固定 3 轮。各字段用途：`opening` 开场白；`question` 该轮客户台词的**参考方向**（AI 生成追问时围绕它）；`keywords` 评分考察关键点；`tips` 教练提示；`bestReply` 满分话术参考。

### 3.6 MotEvent 商机事件（⚠️ 当前在 `pages/mot/mot.js` 内）

```json
{
  "id": 1,
  "time": "09:00",
  "type": "maturity",
  "clientName": "王老板",
  "clientTag": "建材城批发商 | 资产500W+",
  "eventTitle": "【300万大额存单明日到期】",
  "detail": "大额存单 300万 · 明日到期，当日为资金承接黄金窗口",
  "aiStrategy": "客户对资金灵活性要求高……",
  "generatedScript": "王总早上好！您行里那笔300万的存单明天就到期啦……",
  "phone": "138 6688 2391",
  "customerNo": "SCRC20260001",
  "assets": "资产 500W+",
  "risk": "中低风险 R2",
  "traits": "资金周转频繁，重灵活性；……",
  "touch": "白天忙生意，上午 9 点与晚上 8 点后接听率最高"
}
```

`type` 枚举：`maturity`（到期）/ `behavior`（行为追踪）/ `alert`（风险预警）。`aiStrategy` 与 `generatedScript` 适合改为大模型实时生成或预生成入库。

### 3.7 合规违禁词

当前前端词库：`['保本', '稳赚', '刚兑', '零风险', '无风险', '保收益']`，每个词配一条"行内核准替代表述"。**建议服务端建表维护**（词、替代表述、启用状态），前端启动时拉取缓存。

---

## 4. AI 能力契约（后端代理大模型时必须保持的输入输出）

前端已实现的 DeepSeek 调用在 `utils/ai.js`，统一特征：`POST /chat/completions`、`response_format: {type:'json_object'}`、`thinking: {type:'disabled'}`、30s 超时。后端迁移时请保持以下 JSON 契约，前端展示层即可零改动切换。

### 4.1 对练评分 + 客户下一句话（每轮 1 次调用）

**输入**：剧本全量信息 + 当前轮次 + 学员回答 + 完整对话历史

```json
{
  "scriptId": "s01",
  "roundIdx": 0,
  "answer": "学员的回应文本",
  "history": [
    { "role": "customer", "text": "客户说的话" },
    { "role": "manager", "text": "学员说的话" }
  ]
}
```

**输出**：

```json
{
  "score": 85,
  "level": "优秀",
  "comment": "60-120字教练点评",
  "nextQuestion": "客户下一句话（30-60字），最后一轮为 null"
}
```

约束：`score` 0-100 整数；`level` ∈ {优秀(≥85), 良好(70-84), 待提升(<70)}；评分维度 = 关键点覆盖50 + 共情沟通25 + 专业合规25（违禁表述合规项清零）；`nextQuestion` 围绕下一轮 `question` 参考方向生成，须承接学员刚才的回应。

### 4.2 整场总结建议（对练结束 1 次调用）

**输入**：`{ "scriptId": "s01", "history": [...], "grades": [{"score": 85, "level": "优秀"}] }`

**输出**：`{ "advice": "100-160字总结：全场亮点(带轮次举例) → 1-2个共性问题 → 一句行动建议，连贯成段不分点" }`

### 4.3 客户诊断（当前为本地规则引擎，建议升级为 AI）

**输入**：`{ "age": "36-50岁", "amount": "50-100万", "source": "企业闲置资金", "preferences": ["流动性优先", "分散配置"] }`

**输出**（前端 Canvas 与话术展示直接消费，字段缺一不可）：

```json
{
  "score": 62,
  "persona": "平衡成长型客户",
  "radar": [44, 90, 71, 67, 70],
  "radarLabels": ["保本偏好", "流动性需求", "收益追求", "投资经验", "期限接受"],
  "config": { "cash": 15, "fixed": 60, "equity": 25 },
  "matched": [ { "id": "p003", "matchScore": 99, "...": "Product 全字段" } ],
  "talk": {
    "terms": [{ "term": "业绩比较基准 2.05%", "plain": "一万块放一年，利息大概205块上下" }],
    "icebreak":  { "raw": "生硬说法", "plain": "AI 大白话" },
    "interview": { "raw": "...", "plain": "..." },
    "objection": { "raw": "...", "plain": "..." }
  }
}
```

### 4.4 合规检查（建议服务端化，保持实时性可前端双跑）

**输入**：`{ "text": "..." }` → **输出**：`{ "ok": false, "word": "保本", "alternative": "行内核准替代表述" }`

### 4.5 前端兜底约定（后端也要实现）

前端逻辑：**AI 失败 → 自动回退本地 mock 规则**。后端应对齐这一韧性设计：大模型超时/报错时，降级为规则引擎结果（评分可用关键词命中率公式，见 `mock.js#gradeAnswer`），保证接口永远 200。

---

## 5. 建议的 REST API 一览

| 方法 | 路径 | 说明 | 消费页面 |
| --- | --- | --- | --- |
| GET | `/api/products?company=` | 产品列表（支持公司筛选） | home |
| GET | `/api/products/{id}` | 产品详情 | home |
| GET | `/api/companies` | 理财子公司列表 | home |
| GET | `/api/market-report` | 快报卡片 + AI 金句 | home |
| GET | `/api/personas` | 客群画像列表 | client |
| GET | `/api/scripts` | 对练剧本列表（含 rounds） | training |
| GET | `/api/mot/events?date=` | MoT 商机事件 | mot |
| GET | `/api/compliance/words` | 违禁词库（前端缓存） | training |
| POST | `/api/compliance/check` | 违禁词检查 | training |
| POST | `/api/ai/training/grade` | 对练评分 + 客户下一句话（契约见 4.1） | training |
| POST | `/api/ai/training/summary` | 整场总结建议（契约见 4.2） | training |
| POST | `/api/ai/diagnose` | 客户诊断（契约见 4.3） | client |
| POST | `/api/ai/product-insight` | （可选）双产品 AI 穿透点评 | home/compare |
| POST | `/api/agent/chat` | Agent 对话总入口（卡片式响应，契约见 §8） | agent |

统一响应包装建议：`{ "code": 0, "message": "ok", "data": {...} }`。

---

## 6. SOFABoot 工程落地建议

### 6.1 模块划分（Maven 多模块）

```
wealth-copilot-backend/
├── facade/        # DTO、API 接口定义（对本文件第 3、4 节建模）
├── service/       # 业务实现、大模型网关（Prompt 管理、超时重试、规则降级）
├── dal/           # MyBatis Mapper / 实体
└── web/           # REST Controller、启动类
```

### 6.2 关键配置（application.yml，Key 走配置中心/环境变量）

```yaml
deepseek:
  base-url: https://api.deepseek.com/chat/completions
  api-key: ${DEEPSEEK_API_KEY}   # 严禁硬编码进 git
  model: deepseek-flash
  timeout-ms: 30000
```

### 6.3 大模型网关要点

1. **Prompt 即配置**：第 4 节的 system prompt 抽成模板文件/配置项，便于调优不发版
2. **JSON 模式**：请求带 `response_format: {type:'json_object'}` + `thinking: {type:'disabled'}`
3. **解析容错**：正则提取首个 `{...}` 再反序列化（模型可能包裹 markdown 代码块）
4. **降级**：超时/5xx/解析失败 → 规则引擎兜底，接口不返回错误
5. **成本**：对练每轮 1 次调用（评分+追问合并），总结 1 次；`temperature` 评分 0.7 / 总结 0.5

### 6.4 建表示例（MySQL）

```sql
CREATE TABLE product (
  id VARCHAR(16) PRIMARY KEY,
  company VARCHAR(32) NOT NULL,
  name VARCHAR(64) NOT NULL,
  tags JSON,
  nature VARCHAR(16), sale_type VARCHAR(16),
  risk_level VARCHAR(4), min_amount INT,
  term VARCHAR(16), benchmark_yield VARCHAR(8),
  trend JSON, asset_type VARCHAR(128), selling_point VARCHAR(255)
);

CREATE TABLE role_play_script (
  id VARCHAR(16) PRIMARY KEY,
  title VARCHAR(64), difficulty VARCHAR(8),
  persona VARCHAR(255), opening TEXT
);

CREATE TABLE script_round (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  script_id VARCHAR(16), round_no INT,
  question VARCHAR(255), keywords JSON,
  tips VARCHAR(255), best_reply TEXT,
  INDEX idx_script (script_id)
);

CREATE TABLE forbidden_word (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  word VARCHAR(32) UNIQUE, alternative VARCHAR(255), enabled TINYINT DEFAULT 1
);

CREATE TABLE mot_event (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_date DATE, event_time VARCHAR(8), type VARCHAR(16),
  client_name VARCHAR(32), client_tag VARCHAR(64),
  event_title VARCHAR(128), detail VARCHAR(255),
  ai_strategy TEXT, generated_script TEXT,
  phone VARCHAR(16), customer_no VARCHAR(32),
  assets VARCHAR(32), risk VARCHAR(32), traits VARCHAR(255), touch VARCHAR(255)
);
-- company / client_persona / market_report_card 同理从略
```

---

## 7. 联调迁移顺序建议

1. **第一步：纯数据接口**（products/companies/market-report/personas/scripts/mot-events/words）——前端把 `require('../../utils/mock')` 换成 `wx.request`，工作量小、风险低
2. **第二步：AI 代理**（training/grade、training/summary）——前端 `utils/ai.js` 的 `wx.request` URL 从 DeepSeek 改为后端地址，请求体按第 4 节契约包装，**Key 从前端删除**
3. **第三步：诊断与合规**（diagnose、compliance/check 服务端化）
4. **第四步（可选）**：金句、穿透点评、MoT 话术的 AI 化
5. **第五步（第二阶段）**：Agent 助手对话入口（见 §8）

---

## 8. Agent 助手（对话式总入口 · 第二阶段规划）

### 8.1 定位与入口

在小程序新增"AI 助手"作为对话式总入口：理财经理发一句话，后端 Agent 识别意图、调用工具、返回**结构化卡片**。深度操作仍跳回各业务页面完成，Agent 窗口只做调度与生成。

- 入口一：`app.json` tabBar 新增第 4 个 Tab「AI 助手」（当前 3 个，上限 5 个）
- 入口二：工作台首页顶部"问问 AI"输入框，输入后跳转助手页并透传问题

### 8.2 技能清单（skills）

| 技能 | 触发示例 | 工具链 | 输出卡片 | 数据依赖 |
| --- | --- | --- | --- | --- |
| `moments-copy` 朋友圈/群文案 | "写条杭银幸福99的朋友圈，降息主题" | 产品库查询 + 合规检查 | copy | 无（纯生成，**最先落地**） |
| `morning-meeting` 晨会准备 | "帮我准备明天晨会" | 业绩数据 + MoT 事件 + 市场快报聚合 | morning | 现有数据即可 |
| `daily-stats` 每日数据统计 | "今天销售数据怎么样" | 销售数据查询 + 客户动态 | stats | 需接行内数据（Demo 用 mock） |
| `material-digest` 材料消化 | 上传 PDF "帮我消化这份材料" | 文档解析 + 产品库 | digest | 文档解析服务（前端用 `wx.chooseMessageFile` 从微信聊天选文件） |

落地顺序建议：`moments-copy` → `morning-meeting` → `daily-stats` → `material-digest`。

### 8.3 统一接口契约

`POST /api/agent/chat`

**请求**：

```json
{
  "sessionId": "abc123",
  "message": "帮我准备明天晨会",
  "attachments": [{ "type": "image | file", "url": "https://..." }]
}
```

**响应**：

```json
{
  "replyType": "card",
  "cardType": "morning",
  "text": "晨会稿已生成，今日重点关注 3 条商机。",
  "payload": {},
  "suggestions": ["把晨会稿压缩成 3 分钟版", "给今日 3 条商机逐条生成话术"]
}
```

`payload` 按 `cardType` 约定：

| cardType | payload 结构 |
| --- | --- |
| `stats` | `{ "metrics": [{"label","value","trend"}], "insight": "一句话解读" }` |
| `morning` | `{ "speech": "发言稿全文", "agenda": ["议题"], "motRefs": ["motEventId"] }` |
| `copy` | `{ "content": "文案", "compliancePass": true, "complianceNote": "🛡️ 已过合规词库校验" }` |
| `digest` | `{ "summary": "一页纸摘要", "sellingPoints": ["卖点"], "faq": [{"q","a"}] }` |

卡片可携带 `actions`：`[{"label": "查看商机", "action": "navigate", "path": "/pages/mot/mot"}]`，前端据此渲染跳转按钮。

### 8.4 后端编排：Workflow 架构（非全自主 Agent）

四个技能均为固定流程，采用**确定性 Workflow 编排**，LLM 仅作为流程中的"生成节点"；全自主决策只保留在入口意图路由。原则：**Workflow-first**——流程固定、可观测、可单测、成本延迟可控，合规闸门不可绕过。

**节点类型（5 种）**：

| 节点 | 职责 | 实现 |
| --- | --- | --- |
| 工具节点 | 查数据（产品库/MoT/业绩） | 复用 §5 数据接口 |
| 规则节点 | 排序、计算、聚合 | 纯 Java 代码 |
| 生成节点 | 文案/发言稿/摘要 | LLM（§4 契约） |
| 闸门节点 | 合规校验，命中自动改写（≤2 次重试） | §3.7 违禁词库，**固定不可跳过** |
| 等待节点 | 参数不足挂起，追问用户（如"想推哪款产品？"），回复后续跑 | 会话状态机 |

**示例：`morning-meeting` 工作流**

```
触发(意图识别)
  → 并行拉取：【昨日业绩】【今日MoT事件】【市场快报】   ← 工具节点
  → 聚合排序（规则代码）                                ← 规则节点
  → LLM 生成晨会发言稿                                  ← 生成节点
  → 合规词库校验（命中→自动改写，最多重试2次）           ← 闸门节点
  → 组装 morning 卡片返回
```

**技术选型（SOFABoot / Java 生态）**：

- 轻量自编排（推荐起步）：每个技能一个 Spring Service，步骤即方法，`CompletableFuture` 做并行拉取——Demo 与内部工具足够
- 框架化：[LangChain4j](https://github.com/langchain4j/langchain4j) 或 Spring AI（内置 tool calling 与链式编排）
- 平台化（可选）：Dify 等可视化编排平台私有化部署，SOFABoot 只做转发与鉴权

**其他编排要点**：

1. **意图路由**：入口轻量分类（Function Calling），路由到对应 Workflow；无法识别走通用对话
2. **工具注册表**：§4 的 AI 能力、§5 的数据接口直接注册为工具节点，不重复建设
3. **会话记忆**：`sessionId` 维度缓存最近 N 轮（Redis），支撑等待节点的多轮补参；经理长期偏好（常推产品、客群）入库
4. **多模态预留**：`attachments` 支持图片（聊天截图读图，DeepSeek 多模态）与文件（材料消化）

### 8.5 前端改造点

| 文件 | 改造内容 |
| --- | --- |
| `app.json` | tabBar 加第 4 个 Tab；`assets/icons` 补 agent 图标 |
| `pages/agent/`（新增） | 对话页：消息流 + 卡片渲染器（按 cardType）+ `wx.chooseMessageFile` 文件上传 |
| `pages/home/home.wxml` | 顶部加"问问 AI"输入框，跳转助手页并透传问题 |

### 前端改造点速查

| 文件 | 改造内容 |
| --- | --- |
| `utils/ai.js` | 请求地址改为后端 `/api/ai/training/*`；删除 Key 与 `isAIConfigured` 判断 |
| `utils/config.js` | 删除（迁移完成后） |
| `pages/home/home.js` | `onLoad` 中 mock 数据改为接口拉取；`buildInsightParts` 可换 `/api/ai/product-insight` |
| `pages/mot/mot.js` | 内置 `motEvents` 改为 `/api/mot/events` |
| `pages/client/client.js` | `diagnoseClient()` 改为 `POST /api/ai/diagnose` |
| `pages/training/training.js` | `rolePlayScripts` 改为接口拉取；`complianceCheck` 用词库缓存 |
| `pages/compare/compare.js` | `utils/pk.js` 的 PRODUCTS 与主产品库合并统一 |

---

## 附录：当前在用的完整 Prompt（后端直接复用）

### A. 对练评分 system prompt

```
你是一名银行财富管理条线的资深销售培训教练，同时兼任模拟对练中"客户"一角的扮演。
每次收到学员（理财经理）的回应后，你需要完成两件事：
1. 以教练身份为其打分点评；
2. 以客户身份，结合人设与对话历史，自然地说出下一句话。
请严格输出 JSON，不要输出 JSON 以外的任何内容。

评分维度（总分 100）：
1. 关键点覆盖（0-50）：回应是否自然覆盖本轮考察关键点，而非生硬堆砌；
2. 共情与沟通（0-25）：是否先接住客户情绪、表达理解，避免与客户形成对立；
3. 专业与合规（0-25）：数据与事实运用是否准确；若出现承诺收益或"保本""稳赚"等违禁表述，本项得 0 分。

输出 JSON 格式（严格遵守）：
{"score": 0-100的整数, "level": "优秀 或 良好 或 待提升", "comment": "60-120字教练点评", "next_question": "客户的下一句话，30-60字口语化表达；若已是最后一轮则为 null"}
level 判定：score>=85 为优秀，70-84 为良好，其余为待提升。
comment 要求：像教练面谈一样口语化，先肯定一个具体亮点，再指出 1-2 个可执行的改进点；若学员本轮回应与前几轮存在呼应、矛盾或简单重复，请明确点出来。
next_question 要求：必须贴合人设、承接学员刚才的回应——学员说服力强则表现出松动但抛出一个新顾虑，学员回应生硬则更加抗拒；不要重复之前说过的话。
```

### B. 总结建议 system prompt

```
你是一名银行财富管理条线的资深销售培训教练。学员刚完成一场多轮模拟对练，
请基于完整对话历史与各轮得分，给出整场总结性建议，严格输出 JSON，不要输出其他内容。

输出 JSON 格式（严格遵守）：
{"advice": "100-160字的总结建议"}
advice 要求：
1. 先整体肯定一个贯穿全场的亮点（结合具体轮次举例）；
2. 指出 1-2 个反复出现的共性问题（如始终未覆盖某类关键点、共情不足、推进太急等）；
3. 最后给一句可落地的行动建议。
语气像教练复盘面谈，口语化，不要分点、不要列表，连贯成段。
```

---

*文档生成时间：2026-09-14 · 对应前端 main 分支当前版本*
