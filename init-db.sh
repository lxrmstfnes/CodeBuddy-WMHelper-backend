#!/bin/bash
# =============================================================
# 一键初始化本地开发数据库
# 1. 启动 OceanBase + Redis 容器
# 2. 等待 OB 启动完成(首次约 2-5 分钟)
# 3. 建库建表(sql/01-schema.sql)
# 4. 灌入种子数据(sql/02-seed.sql,与前端 mock 数据对齐)
# 重复执行安全:schema 会删表重建,seed 会先清空再插入
# =============================================================
set -e
cd "$(dirname "$0")"

OB_CONTAINER=wealth-ob
OB_USER=test         # test 租户 root 用户(格式: 用户名@租户名见下方 -u 参数)

echo "==> [1/4] 启动 OceanBase + Redis 容器"
docker compose up -d

echo "==> [2/4] 等待 OceanBase 启动完成(首次约 2-5 分钟,请耐心)..."
for i in $(seq 1 90); do
  if docker logs $OB_CONTAINER 2>&1 | grep -q "boot success"; then
    echo "    √ 检测到 boot success"
    break
  fi
  if [ "$i" -eq 90 ]; then
    echo "    × 等待超时(7.5 分钟),请执行 docker logs $OB_CONTAINER 排查"
    exit 1
  fi
  sleep 5
done

# boot success 后再确认 SQL 端口可连(最多再等 60 秒)
echo "    等待 SQL 端口就绪..."
for i in $(seq 1 12); do
  if docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 -e "SELECT 1" >/dev/null 2>&1; then
    echo "    √ SQL 端口可连接"
    break
  fi
  if [ "$i" -eq 12 ]; then
    echo "    × SQL 端口连接失败,请执行 docker logs $OB_CONTAINER 排查"
    exit 1
  fi
  sleep 5
done

echo "==> [3/4] 建库 + 建表"
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/01-schema.sql
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/03-crm-schema.sql

echo "==> [4/4] 灌入种子数据"
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/02-seed.sql
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/04-crm-seed.sql
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/05-intake-schema.sql
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 < sql/06-scripts.sql

echo ""
echo "==> 完成!数据验证:"
docker exec -i $OB_CONTAINER obclient -h127.0.0.1 -P2881 -uroot@test -proot123 -e "
USE wealth_copilot;
SELECT 'product' AS tbl, COUNT(*) AS cnt FROM product
UNION ALL SELECT 'company', COUNT(*) FROM company
UNION ALL SELECT 'client_persona', COUNT(*) FROM client_persona
UNION ALL SELECT 'market_report', COUNT(*) FROM market_report
UNION ALL SELECT 'market_report_card', COUNT(*) FROM market_report_card
UNION ALL SELECT 'role_play_script', COUNT(*) FROM role_play_script
UNION ALL SELECT 'script_round', COUNT(*) FROM script_round
UNION ALL SELECT 'forbidden_word', COUNT(*) FROM forbidden_word
UNION ALL SELECT 'mot_event', COUNT(*) FROM mot_event
UNION ALL SELECT 'customer', COUNT(*) FROM customer
UNION ALL SELECT 'customer_event', COUNT(*) FROM customer_event
UNION ALL SELECT 'follow_task', COUNT(*) FROM follow_task
UNION ALL SELECT 'intake_token', COUNT(*) FROM intake_token
UNION ALL SELECT 'script_item', COUNT(*) FROM script_item;"

echo ""
echo "==> 连接信息(SOFABoot application.yml):"
echo "    url: jdbc:mysql://localhost:2881/wealth_copilot?useSSL=false&serverTimezone=Asia/Shanghai"
echo "    username: root@test"
echo "    password: root123"
