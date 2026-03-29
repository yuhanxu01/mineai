#!/usr/bin/env bash
# =============================================================================
# MineAI 一键部署脚本  ——  Ubuntu 24 LTS  (2核 4G)
# 用法：
#   1. 将整个项目上传到服务器，例如 /home/ubuntu/mineai
#   2. cd /home/ubuntu/mineai
#   3. cp .env.example .env && nano .env   # 填写真实配置
#   4. chmod +x deploy.sh && sudo ./deploy.sh
# =============================================================================
set -euo pipefail

# ── 可改变量 ──────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "$0")" && pwd)"   # 脚本所在目录即项目根目录
APP_USER="${SUDO_USER:-ubuntu}"            # 运行应用的系统用户（非 root）
VENV_DIR="$APP_DIR/.venv"
DOMAIN=""                                  # 留空则跳过 HTTPS 证书申请
NGINX_PORT=80                              # HTTP 端口（有域名时自动配 443）

# ── 颜色输出 ──────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 检查 root ─────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || error "请以 sudo 运行此脚本"

# ── 检查 .env ─────────────────────────────────────────────────
[[ -f "$APP_DIR/.env" ]] || error ".env 文件不存在，请先 cp .env.example .env 并填写配置"
grep -q "your-very-long-random-secret-key" "$APP_DIR/.env" \
    && error "请在 .env 中修改 SECRET_KEY 为真实随机值后再部署"

# ── 读取 .env（仅用于提取 DOMAIN） ───────────────────────────
ALLOWED_HOSTS_LINE=$(grep "^ALLOWED_HOSTS=" "$APP_DIR/.env" || true)
if [[ -n "$ALLOWED_HOSTS_LINE" ]]; then
    FIRST_HOST=$(echo "$ALLOWED_HOSTS_LINE" | cut -d= -f2 | cut -d, -f1 | tr -d ' ')
    # 若第一个 host 看起来像域名（含 .）则作为 DOMAIN
    if [[ "$FIRST_HOST" =~ \. ]] && [[ ! "$FIRST_HOST" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        DOMAIN="$FIRST_HOST"
    fi
fi

# =============================================================================
# 1. 系统依赖
# =============================================================================
info "更新系统并安装依赖..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    build-essential libffi-dev libssl-dev \
    libgl1 libglib2.0-0 \
    nginx \
    git curl ufw

# =============================================================================
# 2. Python 虚拟环境 & 依赖
# =============================================================================
info "创建 Python 虚拟环境..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

info "安装 Python 依赖（首次可能需要几分钟）..."
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" -q

deactivate

# =============================================================================
# 3. 目录权限 & 日志目录
# =============================================================================
info "设置目录权限..."
mkdir -p "$APP_DIR/logs" "$APP_DIR/media" "$APP_DIR/staticfiles" \
         "$APP_DIR/data/ocr" "$APP_DIR/data/scan"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# =============================================================================
# 4. Django 初始化（migrate / collectstatic）
# =============================================================================
info "执行数据库迁移..."
sudo -u "$APP_USER" bash -c "
    source '$VENV_DIR/bin/activate'
    cd '$APP_DIR'
    set -a; source .env; set +a
    export DJANGO_SETTINGS_MODULE=memoryforge.settings_prod
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear
"

# =============================================================================
# 5. Gunicorn systemd 服务
# =============================================================================
info "配置 Gunicorn 服务..."

# 2核4G：worker=2，每 worker 2 线程
cat > /etc/systemd/system/mineai.service <<EOF
[Unit]
Description=MineAI Gunicorn Server
After=network.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
Environment=DJANGO_SETTINGS_MODULE=memoryforge.settings_prod
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 2 \\
    --threads 2 \\
    --worker-class gthread \\
    --bind unix:$APP_DIR/mineai.sock \\
    --timeout 120 \\
    --keep-alive 5 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --access-logfile $APP_DIR/logs/gunicorn_access.log \\
    --error-logfile  $APP_DIR/logs/gunicorn_error.log \\
    --log-level warning \\
    memoryforge.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mineai
systemctl restart mineai

# 等待 sock 创建
sleep 2
if [[ ! -S "$APP_DIR/mineai.sock" ]]; then
    warn "Gunicorn socket 未创建，请检查日志：journalctl -u mineai -n 50"
fi

# =============================================================================
# 6. Nginx 配置
# =============================================================================
info "配置 Nginx..."

NGINX_SERVER_NAME="${DOMAIN:-_}"

cat > /etc/nginx/sites-available/mineai <<NGINX_CONF
# ── 限速区（防刷）──────────────────────────────────────────
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=30r/m;
limit_req_zone \$binary_remote_addr zone=auth_limit:10m rate=10r/m;

server {
    listen 80;
    server_name $NGINX_SERVER_NAME;

    client_max_body_size 50M;
    keepalive_timeout 65;

    # ── 安全响应头 ──────────────────────────────────────────
    add_header X-Content-Type-Options   nosniff;
    add_header X-Frame-Options          SAMEORIGIN;
    add_header X-XSS-Protection         "1; mode=block";
    add_header Referrer-Policy          "strict-origin-when-cross-origin";

    # ── 静态文件（直接由 Nginx 服务）──────────────────────
    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /media/ {
        alias $APP_DIR/media/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }

    # ── 认证接口限速（防暴力破解）──────────────────────────
    location /api/auth/ {
        limit_req zone=auth_limit burst=5 nodelay;
        proxy_pass http://unix:$APP_DIR/mineai.sock;
        include /etc/nginx/proxy_params;
    }

    # ── SSE 流式接口（禁止缓冲）────────────────────────────
    location ~ ^/api/(novel|code|core|kg|paper|scan|bridge)/ {
        proxy_pass http://unix:$APP_DIR/mineai.sock;
        include /etc/nginx/proxy_params;
        proxy_buffering         off;
        proxy_cache             off;
        proxy_read_timeout      300s;
        proxy_send_timeout      300s;
        add_header X-Accel-Buffering no;
    }

    # ── 普通 API ────────────────────────────────────────────
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://unix:$APP_DIR/mineai.sock;
        include /etc/nginx/proxy_params;
    }

    # ── 前端 SPA ────────────────────────────────────────────
    location / {
        proxy_pass http://unix:$APP_DIR/mineai.sock;
        include /etc/nginx/proxy_params;
    }
}
NGINX_CONF

# proxy_params（如不存在则创建）
if [[ ! -f /etc/nginx/proxy_params ]]; then
    cat > /etc/nginx/proxy_params <<'PP'
proxy_set_header Host              $http_host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
PP
fi

# 启用站点
ln -sf /etc/nginx/sites-available/mineai /etc/nginx/sites-enabled/mineai
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

# =============================================================================
# 7. HTTPS（可选，需要域名 + DNS 已指向本机）
# =============================================================================
if [[ -n "$DOMAIN" ]]; then
    info "检测到域名 $DOMAIN，尝试申请 Let's Encrypt 证书..."
    if apt-get install -y -qq certbot python3-certbot-nginx; then
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
            --email "$(grep EMAIL_HOST_USER "$APP_DIR/.env" | cut -d= -f2 | tr -d ' ')" \
            --redirect || warn "certbot 申请证书失败，请手动执行：certbot --nginx -d $DOMAIN"
        systemctl reload nginx
    fi
else
    info "未检测到域名，跳过 HTTPS 配置（后续可手动运行 certbot）"
fi

# =============================================================================
# 8. 防火墙
# =============================================================================
info "配置 UFW 防火墙..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# =============================================================================
# 9. 每日备份 cron（SQLite）
# =============================================================================
info "配置每日数据库备份..."
BACKUP_SCRIPT="/usr/local/bin/mineai_backup.sh"
cat > "$BACKUP_SCRIPT" <<BACKUP
#!/bin/bash
BACKUP_DIR="$APP_DIR/backups"
mkdir -p "\$BACKUP_DIR"
# 保留最近 7 天
find "\$BACKUP_DIR" -name "db_*.sqlite3" -mtime +7 -delete
cp "$APP_DIR/db.sqlite3" "\$BACKUP_DIR/db_\$(date +%Y%m%d_%H%M%S).sqlite3"
BACKUP
chmod +x "$BACKUP_SCRIPT"

# 每天凌晨 3 点备份
(crontab -l 2>/dev/null | grep -v mineai_backup; echo "0 3 * * * $BACKUP_SCRIPT") | crontab -

# =============================================================================
# 完成
# =============================================================================
echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}  MineAI 部署完成！${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo "  服务状态：  sudo systemctl status mineai"
echo "  应用日志：  tail -f $APP_DIR/logs/gunicorn_error.log"
echo "  Nginx日志：  tail -f /var/log/nginx/error.log"
echo ""
if [[ -n "$DOMAIN" ]]; then
    echo "  访问地址：  https://$DOMAIN"
else
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "  访问地址：  http://$SERVER_IP"
    echo "  提示：配置域名后可运行 certbot --nginx -d <域名> 开启 HTTPS"
fi
echo ""
echo "  创建管理员账号："
echo "    cd $APP_DIR"
echo "    source .venv/bin/activate"
echo "    DJANGO_SETTINGS_MODULE=memoryforge.settings_prod python manage.py createsuperuser"
echo ""
