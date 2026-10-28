#!/bin/bash
# ====================
# Docker 构建脚本 - 优化版
# 支持构建缓存、增量构建、多平台构建
# ====================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 默认值
BUILD_TARGET="all"
PUSH_IMAGE=false
USE_CACHE=true
IMAGE_TAG="latest"

# 帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
    -t, --target      构建目标: backend|frontend|all (默认: all)
    -p, --push        构建后推送到镜像仓库
    -n, --no-cache    不使用构建缓存
    -r, --tag         镜像标签 (默认: latest)
    -h, --help        显示帮助信息

示例:
    $0                      # 构建所有镜像
    $0 -t backend           # 只构建后端
    $0 -t frontend -p      # 构建前端并推送
    $0 -t all -n           # 不使用缓存重新构建
EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            BUILD_TARGET="$2"
            shift 2
            ;;
        -p|--push)
            PUSH_IMAGE=true
            shift
            ;;
        -n|--no-cache)
            USE_CACHE=false
            shift
            ;;
        -r|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 构建参数
DOCKER_BUILD_ARGS="--pull"
if [ "$USE_CACHE" = true ]; then
    DOCKER_BUILD_ARGS="--pull"
else
    DOCKER_BUILD_ARGS="--pull --no-cache"
fi

# 日志函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 构建后端
build_backend() {
    log_info "开始构建后端镜像..."
    docker build \
        $DOCKER_BUILD_ARGS \
        -f Dockerfile.backend \
        -t "xiaoju-backend:${IMAGE_TAG}" \
        --platform linux/amd64 \
        --platform linux/arm64 \
        .

    log_info "后端镜像构建完成: xiaoju-backend:${IMAGE_TAG}"

    if [ "$PUSH_IMAGE" = true ]; then
        docker push "xiaoju-backend:${IMAGE_TAG}"
        log_info "后端镜像已推送"
    fi
}

# 构建前端
build_frontend() {
    log_info "开始构建前端镜像..."
    docker build \
        $DOCKER_BUILD_ARGS \
        -f Dockerfile.frontend \
        -t "xiaoju-frontend:${IMAGE_TAG}" \
        --platform linux/amd64 \
        --platform linux/arm64 \
        .

    log_info "前端镜像构建完成: xiaoju-frontend:${IMAGE_TAG}"

    if [ "$PUSH_IMAGE" = true ]; then
        docker push "xiaoju-frontend:${IMAGE_TAG}"
        log_info "前端镜像已推送"
    fi
}

# 显示配置
echo "=========================================="
echo " 小火炬一键多发 - Docker 构建"
echo "=========================================="
echo " 目标: ${BUILD_TARGET}"
echo " 标签: ${IMAGE_TAG}"
echo " 使用缓存: ${USE_CACHE}"
echo " 推送镜像: ${PUSH_IMAGE}"
echo "=========================================="

# 执行构建
case "$BUILD_TARGET" in
    backend)
        build_backend
        ;;
    frontend)
        build_frontend
        ;;
    all)
        build_backend
        build_frontend
        ;;
    *)
        log_error "无效的构建目标: $BUILD_TARGET"
        show_help
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN} 构建完成！${NC}"
echo "=========================================="
echo ""
echo "启动服务: docker-compose up -d"
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo "完全清理: docker-compose down -v --rmi all"
echo ""
