#!/bin/bash
# =============================================
# 解忧树洞 - 一键部署脚本
# 使用方法：
#   1. 把 shudong-vercel 文件夹解压
#   2. cd shudong-vercel
#   3. bash deploy.sh
# =============================================
set -e

echo "🌳 解忧树洞 - 一键部署"
echo "========================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 请先安装 Node.js: https://nodejs.org"
    exit 1
fi
echo "✅ Node.js: $(node -v)"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ 请先安装 npm"
    exit 1
fi
echo "✅ npm: $(npm -v)"

# 安装 Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "📦 安装 Vercel CLI..."
    npm install -g vercel
fi
echo "✅ Vercel CLI: $(vercel --version 2>&1 | head -1)"

echo ""
echo "🔑 接下来会打开浏览器，请用 GitHub/Google 登录 Vercel"
echo "   按回车继续..."
read

# 登录
vercel login

echo ""
echo "📝 设置管理员密码（默认 admin123）:"
read ADMIN_PWD
ADMIN_PWD=${ADMIN_PWD:-admin123}

echo ""
echo "🚀 开始部署..."
echo ""

# 部署
vercel \
  --env DATABASE_URL="postgresql://neondb_owner:npg_8jWxGPhOdU0M@ep-damp-hill-aykqd8bu.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  --env ADMIN_PASSWORD="$ADMIN_PWD" \
  --prod

echo ""
echo "================================="
echo "🎉 部署完成！"
echo ""
echo "管理员密码: $ADMIN_PWD"
echo "右下角 🔐 按钮 → 输入密码 → 进入后台"
echo ""
echo "数据存储在 Neon PostgreSQL，永久保存，除非管理员删除。"
echo "================================="
