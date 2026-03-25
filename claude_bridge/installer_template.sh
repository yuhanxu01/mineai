#!/bin/bash
# Claude Bridge One-Liner Installer
set -e

# These will be replaced by the platform at delivery time
PLATFORM_URL="__PLATFORM_URL__"
USER_TOKEN="__USER_TOKEN__"

BRIDGE_DIR="$HOME/.claude-bridge"
VENV_DIR="$BRIDGE_DIR/venv"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         Claude Bridge  Installer             ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Dependency Checks
info "检查系统依赖..."

if ! command -v python3 &> /dev/null; then
    error "未找到 python3，请先安装 Python 3.8+。"
fi

if ! command -v node &> /dev/null; then
    error "未找到 node (Node.js)，请先安装 Node.js。"
fi

if ! command -v npm &> /dev/null; then
    error "未找到 npm，请先安装 Node.js (含 npm)。"
fi

# 2. Claude Code CLI
if ! command -v claude &> /dev/null; then
    info "正在全局安装 @anthropic-ai/claude-code..."
    if command -v sudo &> /dev/null; then
        sudo npm install -g @anthropic-ai/claude-code || error "安装 claude-code 失败。"
    else
        npm install -g @anthropic-ai/claude-code || error "安装 claude-code 失败。"
    fi
    ok "Claude Code CLI 已安装。"
else
    ok "Claude Code CLI 已就绪: $(claude --version)"
fi

# 3. Setup Directory
info "初始化目录: $BRIDGE_DIR..."
mkdir -p "$BRIDGE_DIR"

# 4. Download Bridge Client
info "下载桥接客户端..."
curl -sSL "$PLATFORM_URL/api/bridge/client/script/" \
     -H "Authorization: Token $USER_TOKEN" \
     -o "$BRIDGE_DIR/bridge.py" || error "下载 bridge.py 失败。"
chmod +x "$BRIDGE_DIR/bridge.py"

# 5. Virtual Environment
info "创建 Python 虚拟环境..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install requests -q || error "安装 requests 依赖失败。"

# 6. Service Setup
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Linux" ]; then
    if command -v systemctl &> /dev/null; then
        info "配置 systemd 服务 (claude-bridge)..."
        cat <<EOF | sudo tee /etc/systemd/system/claude-bridge.service > /dev/null
[Unit]
Description=Claude Bridge Client
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$VENV_DIR/bin/python3 $BRIDGE_DIR/bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable claude-bridge
        sudo systemctl start claude-bridge
        ok "systemd 服务已创建并启动。"
    else
        warn "未找到 systemctl，无法配置自动启动。请手动运行: $VENV_DIR/bin/python3 $BRIDGE_DIR/bridge.py"
    fi
elif [ "$OS_TYPE" == "Darwin" ]; then
    info "配置 macOS LaunchAgent..."
    PLIST_PATH="$HOME/Library/LaunchAgents/com.mineai.claude-bridge.plist"
    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mineai.claude-bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$BRIDGE_DIR/bridge.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$BRIDGE_DIR/out.log</string>
    <key>StandardErrorPath</key>
    <string>$BRIDGE_DIR/err.log</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    ok "macOS LaunchAgent 已创建并加载。"
fi

# 7. Helper Command
info "创建快捷命令 'claude-bridge'..."
cat <<EOF | sudo tee /usr/local/bin/claude-bridge > /dev/null
#!/bin/bash
OS_TYPE=\$(uname)
case "\$1" in
    start)
        if [ "\$OS_TYPE" == "Linux" ]; then sudo systemctl start claude-bridge; else launchctl load "$HOME/Library/LaunchAgents/com.mineai.claude-bridge.plist"; fi
        ;;
    stop)
        if [ "\$OS_TYPE" == "Linux" ]; then sudo systemctl stop claude-bridge; else launchctl unload "$HOME/Library/LaunchAgents/com.mineai.claude-bridge.plist"; fi
        ;;
    restart)
        if [ "\$OS_TYPE" == "Linux" ]; then sudo systemctl restart claude-bridge; else launchctl unload "$HOME/Library/LaunchAgents/com.mineai.claude-bridge.plist" && launchctl load "$HOME/Library/LaunchAgents/com.mineai.claude-bridge.plist"; fi
        ;;
    status)
        if [ "\$OS_TYPE" == "Linux" ]; then sudo systemctl status claude-bridge; else launchctl list | grep claude-bridge; fi
        ;;
    logs)
        if [ "\$OS_TYPE" == "Linux" ]; then journalctl -u claude-bridge -f; else tail -f "$BRIDGE_DIR/out.log" "$BRIDGE_DIR/err.log"; fi
        ;;
    *)
        echo "用法: claude-bridge {start|stop|restart|status|logs}"
        ;;
esac
EOF
sudo chmod +x /usr/local/bin/claude-bridge 2>/dev/null || true

echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}  Claude Bridge 部署完成！${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo "  管理命令:  claude-bridge {start|stop|restart|status|logs}"
echo "  代码目录:  $BRIDGE_DIR"
echo ""
echo "  现在，您可以在平台网页上看到您的设备已上线。"
echo ""
