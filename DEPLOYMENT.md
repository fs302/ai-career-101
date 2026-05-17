# AI-Career-101 部署文档

## 快速启动

### 1. 启动后端服务
```bash
cd /root/.openclaw/workspace/ai-career-101
python3 -m uvicorn web.app:app --host 0.0.0.0 --port 7860
```

### 2. 配置反向代理（可选，用于域名访问）

安装 Caddy：
```bash
apt install -y caddy
```

配置 `/etc/caddy/Caddyfile`：
```caddy
ai-career.findshine.com {
  reverse_proxy localhost:7860
}
```

启动 Caddy：
```bash
caddy run --config /etc/caddy/Caddyfile
```

## 域名配置

- 域名：`ai-career.findshine.com`
- DNS：A记录指向服务器 IP `43.156.49.111`
- SSL：Let's Encrypt 自动配置

## 开机自启

### 后端服务
创建启动脚本 `/root/start-ai-career.sh`：
```bash
#!/bin/bash
cd /root/.openclaw/workspace/ai-career-101
python3 -m uvicorn web.app:app --host 0.0.0.0 --port 7860 >> /root/.openclaw/workspace/ai-career-101/server.log 2>&1 &
sleep 3
caddy run --config /etc/caddy/Caddyfile >> /root/caddy.log 2>&1 &
```

添加开机启动：
```bash
chmod +x /root/start-ai-career.sh
echo "@reboot /root/start-ai-career.sh" | crontab -
```

### Caddy 服务
```bash
systemctl enable caddy
```

## 环境变量配置

复制 `.env.example` 为 `.env` 并配置：
```bash
cp .env.example .env
```

必需变量：
- `SJTU_API_KEY`：上海交大模型 API Key
- `SJTU_BASE_URL`：API 基础 URL
- `SJTU_TEXT_MODEL`：文本模型（默认 minimax-m2.7）
- `SJTU_VISION_MODEL`：视觉模型（默认 qwen3.5-27b）

## 常用命令

### 查看服务状态
```bash
ps aux | grep uvicorn
ss -tlnp | grep 7860
```

### 重启服务
```bash
pkill -f uvicorn
cd /root/.openclaw/workspace/ai-career-101
python3 -m uvicorn web.app:app --host 0.0.0.0 --port 7860 &
```

### 查看日志
```bash
tail -f /root/.openclaw/workspace/ai-career-101/server.log
tail -f /root/caddy.log
```

## Git 部署

推送代码：
```bash
git remote set-url origin https://<TOKEN>@github.com/fs302/ai-career-101.git
git push origin main
```

## 多子域名配置

在 `/etc/caddy/Caddyfile` 中添加：
```caddy
blog.findshine.com {
  reverse_proxy localhost:8080
}

store.findshine.com {
  reverse_proxy localhost:9090
}
```
