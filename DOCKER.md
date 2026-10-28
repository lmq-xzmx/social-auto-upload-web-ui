# Docker 部署指南 - 优化版

## 概述

本文档描述小火炬一键多发的 Docker 部署方案，采用以下优化技术：

| 优化技术 | 效果 |
|----------|------|
| 多阶段构建 | 镜像体积减少 50-70% |
| Alpine 基础镜像 | 基础镜像从 80MB → 5MB |
| 层优化 | 利用 Docker 缓存，加快构建 |
| 非 root 用户 | 提升安全性 |
| 健康检查 | 自动故障检测与恢复 |
| 资源限制 | 防止容器耗尽主机资源 |
| 日志轮转 | 防止日志撑爆磁盘 |
| Gzip 压缩 | 减少传输体积 60-70% |

---

## 快速开始

### 1. 构建镜像

```bash
# 构建所有服务
./build-docker.sh

# 只构建后端
./build-docker.sh -t backend

# 重新构建（不使用缓存）
./build-docker.sh -n

# 构建并推送
./build-docker.sh -p -r v1.0.0
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 访问应用

- **前端**: http://localhost:5002
- **后端 API**: http://localhost:5004

---

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                      Docker Host                          │
│                                                          │
│  ┌──────────────┐          ┌──────────────────────────┐ │
│  │   Frontend   │          │         Backend          │ │
│  │  (Nginx)     │  proxy  │   (Flask + Waitress)    │ │
│  │  Alpine      │◄────────►│   Python 3.12          │ │
│  │  :80         │          │   :5004                 │ │
│  └──────────────┘          └──────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Volume: xiaoju-data                  │   │
│  │  /app/data → ./data (SQLite, Cookies, Uploads)  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `Dockerfile.backend` | 后端多阶段构建配置 |
| `Dockerfile.frontend` | 前端多阶段构建配置 |
| `docker-compose.yml` | 服务编排配置 |
| `nginx.conf` | Nginx 反向代理配置 |
| `build-docker.sh` | 自动化构建脚本 |
| `.dockerignore` | 构建上下文排除 |

---

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f backend   # 只看后端
docker-compose logs -f frontend   # 只看前端

# 重启服务
docker-compose restart
docker-compose restart backend

# 停止服务
docker-compose down

# 重新构建（代码更新后）
docker-compose build --no-cache
docker-compose up -d

# 完全清理（删除镜像）
docker-compose down -v --rmi all

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh
```

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SAU_PORT` | 5004 | 后端监听端口 |
| `SAU_DATA_DIR` | /app/data | 数据存储目录 |
| `PYTHONUNBUFFERED` | 1 | 实时输出日志 |
| `PYTHONDONTWRITEBYTECODE` | 1 | 不生成 .pyc 文件 |

### 端口映射

| 服务 | 容器端口 | 主机端口 |
|------|----------|----------|
| 前端 (Nginx) | 80 | 5002 |
| 后端 (Flask) | 5004 | 5004 |

### 数据卷

| 主机路径 | 容器路径 | 说明 |
|----------|----------|------|
| `./data` | /app/data | 数据库、Cookie、上传文件 |

---

## 数据库说明

本项目使用 **SQLite** 数据库，存储在数据卷中：

- 数据库文件: `data/db/database.db`
- Cookie 文件: `data/cookies/`
- 上传素材: `data/uploads/`

### 数据备份

```bash
# 备份数据卷
docker run --rm -v xiaoju_xiaoju-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data

# 恢复数据卷
docker run --rm -v xiaoju_xiaoju-data:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /
```

---

## 健康检查

容器内置健康检查：

- **后端**: 每 30 秒检查 `http://localhost:5004/`
- **前端**: 每 30 秒检查 `http://localhost/`

健康检查失败时，容器会自动重启。

---

## 资源限制

### 当前配置

| 服务 | 内存限制 | 内存预留 |
|------|----------|----------|
| 后端 | 2GB | 512MB |
| 前端 | 256MB | 64MB |

### 调整资源限制

编辑 `docker-compose.yml` 中的 `deploy.resources`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G    # 增加到 4GB
        reservations:
          memory: 1G   # 预留 1GB
```

---

## 日志管理

日志配置：
- 最大文件大小: 50MB
- 最大文件数: 3 个

```bash
# 查看后端日志
docker-compose logs backend | tail -100

# 实时跟踪日志
docker-compose logs -f backend

# 清空日志
docker-compose logs -f --tail=0 backend > /dev/null 2>&1
```

---

## 故障排查

### 后端启动失败

```bash
# 查看日志
docker-compose logs backend

# 检查端口占用
lsof -i :5004

# 进入容器排查
docker-compose exec backend bash
```

### 前端无法访问

```bash
# 检查 Nginx 日志
docker-compose logs frontend

# 检查后端是否正常
curl http://localhost:5004/

# 检查网络连接
docker-compose exec frontend ping backend
```

### 数据库问题

```bash
# 检查数据库文件
docker-compose exec backend ls -la /app/data/db/

# 验证数据库
docker-compose exec backend python -c "import sqlite3; sqlite3.connect('/app/data/db/database.db')"
```

---

## 生产环境建议

### 1. 安全加固

```yaml
# 添加安全配置
services:
  backend:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

### 2. 外部数据库（可选）

如需使用 MySQL/PostgreSQL:

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=mysql://user:pass@db:3306/sau
  db:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_DATABASE: sau
    volumes:
      - mysql-data:/var/lib/mysql
```

### 3. HTTPS 配置

在 Nginx 前加一层反向代理（如 Caddy）处理 HTTPS：

```yaml
services:
  caddy:
    image: caddy:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    depends_on:
      - frontend
```

### 4. 监控告警

```yaml
services:
  backend:
    monitoring:
      prometheus.io/port: "5004"
      prometheus.io/path: "/metrics"
```

---

## 镜像体积对比

| 优化前 | 优化后 | 减少 |
|--------|--------|------|
| 后端: ~800MB+ | 后端: ~300-400MB | ~50% |
| 前端: ~200MB+ | 前端: ~30-50MB | ~75% |

---

## 更新流程

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建
docker-compose build --no-cache

# 3. 滚动更新
docker-compose up -d

# 4. 验证
curl http://localhost:5002/
```

---

*文档更新时间: 2026-10-04*
