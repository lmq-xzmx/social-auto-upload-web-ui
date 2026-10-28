# =====================================================
# Stage 1: Build
# =====================================================
FROM node:20-slim AS builder

WORKDIR /app

# 安装依赖（包括 devDependencies）
COPY package*.json ./
RUN npm ci

# 复制源码并构建
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# =====================================================
# Stage 2: Production
# =====================================================
FROM node:20-slim

WORKDIR /app

# 安装生产依赖
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# 复制构建产物
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# 环境变量默认值
ENV TRANSPORT_MODE=both
ENV MCP_PORT=5410
ENV BACKEND_URL=http://social-auto-upload-backend:5409
ENV DB_PATH=/data/db/database.db

# 暴露端口
EXPOSE 5410

# 启动命令
CMD ["node", "dist/index.js"]
