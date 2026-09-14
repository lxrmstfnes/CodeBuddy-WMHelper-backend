# 本地开发 Docker 镜像清单

> 对应 `BACKEND_SPEC.md` 技术栈:SOFABoot + **OceanBase**(§6.4 建表,MySQL 租户模式)+ Redis(§8.4 会话记忆)。
> 用途:本地开发时跑**依赖中间件**;SOFABoot 应用本身在 IDE 中运行,不打镜像。

## 必拉镜像

| 镜像 | 标签 | 用途 | 对应规格章节 | 大约体积 |
| --- | --- | --- | --- | --- |
| `oceanbase/oceanbase-ce` | `latest`(4.x) | 业务数据库(product / role_play_script / mot_event 等 7 张表),MySQL 租户模式 | §6.4 | ~1 GB+ |
| `redis` | `7` | Agent 会话记忆缓存(sessionId 多轮对话) | §8.4 | ~130 MB |

## 拉取命令

```bash
docker pull oceanbase/oceanbase-ce
docker pull redis:7
```

## 可选镜像(按需)

| 镜像 | 标签 | 用途 |
| --- | --- | --- |
| `adminer` | `latest` | 轻量数据库 Web 管理界面(支持 MySQL 协议,可连 OB 的 MySQL 租户) |

```bash
docker pull adminer:latest   # 可选
```

## 验证拉取结果

```bash
docker images
# 期望看到:
# oceanbase/oceanbase-ce   latest
# redis                    7
```

## 端口规划(与本机约定)

| 服务 | 容器端口 | 映射到本机 | 说明 |
| --- | --- | --- | --- |
| OceanBase | 2881 | 2881 | SOFABoot `spring.datasource` 连接(注意不是 3306) |
| Redis | 6379 | 6379 | 第二阶段才启用,先起着无妨 |
| Adminer(可选) | 8080 | 8081 | 避开与后端 8080 冲突 |

## OceanBase 本地运行要点(与 MySQL 的差异)

1. **资源要求高**:OB 比 MySQL 重得多,Docker Desktop 建议分配 ≥ 4C8G;
   资源紧张可用 slim 模式启动:`docker run -e MODE=slim ...`
2. **启动慢**:首次初始化集群要 2-5 分钟,`docker logs -f <容器>` 看到 `boot success` 才算就绪
3. **连接方式(MySQL 租户)**:用户名带租户后缀
   ```bash
   mysql -h127.0.0.1 -P2881 -uroot@test   # test 为默认 MySQL 模式租户,root 初始空密码
   ```
4. **JDBC 连接**:仍可用 `mysql-connector-j` 驱动(协议兼容),或蚂蚁官方 `oceanbase-client`
   ```yaml
   spring:
     datasource:
       url: jdbc:mysql://localhost:2881/wealth_copilot?useSSL=false&serverTimezone=Asia/Shanghai
       username: root@test      # 格式:用户名@租户名
       password: ""
   ```
5. **建库建表**:启动后需手动 `CREATE DATABASE wealth_copilot;` 再执行 §6.4 的 DDL
   (OB 镜像不支持 MySQL 镜像那种 `/docker-entrypoint-initdb.d` 自动初始化)
6. **§6.4 DDL 兼容性**:MySQL 租户模式下 `JSON` 类型、`AUTO_INCREMENT`、索引语法均兼容,可直接执行

## 快速开始(2026-09-14 起)

```bash
./init-db.sh            # 首次:起容器 + 等 OB 就绪 + 建表 + 灌种子数据(约 3-6 分钟)
docker compose up -d    # 日常启动
docker compose down     # 停止(数据保留)
```

| 文件 | 说明 |
| --- | --- |
| `docker-compose.yml` | OceanBase(slim 模式,端口 2881)+ Redis(6379) |
| `sql/01-schema.sql` | 9 张表 DDL(§3 数据模型),幂等可重复执行 |
| `sql/02-seed.sql` | 种子数据,与前端 `mock.js` / `mot.js` 1:1 对齐 |
| `init-db.sh` | 一键初始化(重复执行会删表重建,仅限开发环境) |

连接信息:`jdbc:mysql://localhost:2881/wealth_copilot?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=UTF-8`,用户 `root@test`,空密码。
(⚠️ `characterEncoding=UTF-8` 必须带,否则中文经 JDBC 写入/读取可能乱码)

## 开发环境前提:本地外网

当前为**本地外网开发**(无行内内网访问权限),结论:

- **OceanBase 必须本地容器化**:连不到内网 OB 集群,本地 Docker 是唯一选择
- **外网可直接访问**:Docker Hub(拉镜像)、Maven Central(SOFABoot 依赖)、DeepSeek API(AI 联调)均畅通
- **Docker Hub 拉取慢/失败时**:在 Docker Desktop → Settings → Docker Engine 配置 `registry-mirrors` 镜像加速器后重试
- **未来迁移内网时注意**:镜像需 `docker save` 导出或推送到行内私有 registry;DeepSeek API 在内网需走网关/白名单,届时提前申请

## 备注

- Redis 第一阶段(§5 纯数据接口)不依赖,可暂缓启动;镜像先拉好备用
- 镜像只需拉取一次,之后 `docker compose up -d` 直接使用本地缓存
- 数据持久化靠 volume,`docker compose down` 不会丢数据;`down -v` 才会清空

---
*记录时间:2026-09-14 · 数据库选型:OceanBase(MySQL 租户模式)*
