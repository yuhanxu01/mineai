# SillyTavern 多用户部署指南

## 一、服务器安装

```bash
# 要求：Node.js >= 20
git clone https://github.com/SillyTavern/SillyTavern.git /opt/SillyTavern
cd /opt/SillyTavern
npm install
```

## 二、config.yaml 核心配置

编辑 `/opt/SillyTavern/config.yaml`（首次运行后自动生成）：

```yaml
# 监听所有网络接口（反向代理场景必须开启）
listen: true
port: 8001

# 多用户模式（核心配置）
enableUserAccounts: true
enableDiscreetLogin: true   # 隐藏登录页用户列表，提高安全性

# 关闭白名单（允许来自 Django/Nginx 的代理请求）
whitelistMode: false

# 会话永不过期（可选，按需调整）
sessionTimeout: -1
```

## 三、允许 iframe 嵌入（可选）

SillyTavern 默认设置 `X-Frame-Options: SAMEORIGIN`，如需在 MineAI 内嵌 iframe，
需修改 `server.js`（或 `src/server-main.js`），找到 helmet 配置并禁用 frameguard：

```js
// 找到类似这行：
app.use(helmet({ ... }));

// 改为：
app.use(helmet({ frameguard: false }));
```

> 如果使用独立子域名（推荐），则 iframe 同域问题不存在，无需此步骤。

## 四、PM2 持久运行

```bash
npm install -g pm2
cd /opt/SillyTavern
pm2 start server.js --name sillytavern
pm2 save
pm2 startup   # 按提示执行输出的命令，实现开机自启
```

常用命令：
```bash
pm2 status            # 查看状态
pm2 logs sillytavern  # 查看日志
pm2 restart sillytavern
pm2 stop sillytavern
```

## 五、Nginx 反向代理（推荐：独立子域名）

```nginx
server {
    listen 80;
    server_name tavern.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name tavern.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/tavern.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tavern.yourdomain.com/privkey.pem;

    # WebSocket 支持（SillyTavern 必需）
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;

        # 如需允许 iframe 嵌入（配合上文 frameguard: false）
        add_header X-Frame-Options "ALLOWALL";
    }
}
```

## 六、在 MineAI 管理后台配置

1. 登录 MineAI，进入 **SillyTavern** 应用
2. 点击右上角「管理」按钮（仅管理员可见）
3. 填写：
   - **服务地址**：`https://tavern.yourdomain.com`（或 `http://localhost:8001`）
   - **data 目录路径**：`/opt/SillyTavern/data`
   - 可选填写用户说明文字

## 七、用户使用流程

1. 用户进入 **SillyTavern** 应用
2. 点击「**创建我的账号**」→ 系统自动在 ST 数据目录创建账号
3. 点击「**在新标签页打开**」→ 跳转到 SillyTavern 登录页
4. 用页面上显示的用户名和密码登录
5. 登录后 Cookie 保留，之后可直接使用「**在页面内嵌入**」模式

## 八、注意事项

- SillyTavern 的 API Key 由用户在 ST 界面自行配置（Settings → API Connections）
- MineAI 只负责账号创建，不干预 ST 内部的 AI 接口配置
- 用户数据隔离：每个用户独立的 `/opt/SillyTavern/data/{handle}/` 目录
- 数据备份：定期备份 `/opt/SillyTavern/data/` 目录即可
