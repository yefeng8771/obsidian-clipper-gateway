# 部署指南

从一台空 VPS 到全栈跑起来，完整流程。

## 0. 前置

| 项   | 要求                                                                      |
| ---- | ------------------------------------------------------------------------- |
| VPS  | ≥ 1 GB 内存，≥ 10 GB 磁盘                                                 |
| OS   | 任意 Linux（推荐 Debian 12 / Ubuntu 22.04）                               |
| 域名 | 你拥有控制权的一级或二级域名                                              |
| DNS  | 两条 A 记录（或 AAAA）：`example.com` 和 `sync.example.com` 都指向 VPS IP |
| 软件 | Docker + Docker Compose plugin                                            |

如果 VPS 没装 Docker：

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
```

## 1. 防火墙 / 安全组

只放 22 / 80 / 443 进来：

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

云厂商安全组同步开放这三个端口，**不要暴露 8000 / 9000 到公网**——它们走 Traefik 内部网络即可。

## 2. 拉仓库

```bash
git clone https://github.com/yefeng8771/obsidian-clipper-gateway.git
cd obsidian-clipper-gateway
```

## 3. 准备凭据

### 3.1 必填

| 变量         | 怎么拿                                   |
| ------------ | ---------------------------------------- |
| `DOMAIN`     | 你的域名，例：`example.com`              |
| `ACME_EMAIL` | 任意你常用的邮箱（Let's Encrypt 通知用） |
| `API_KEY`    | `openssl rand -hex 32`，给客户端鉴权     |
| `FNS_TOKEN`  | 第 5 步在 fast-note-sync 后台生成        |

### 3.2 浏览器扩展剪藏要用到

| 变量                  | 怎么拿                                                                       |
| --------------------- | ---------------------------------------------------------------------------- |
| `GITHUB_REPO`         | 一个用来托管 HTML 快照的 repo，建议私有 + 启用 Pages                         |
| `GITHUB_TOKEN`        | 在 https://github.com/settings/tokens 建一个，授权到上面 repo 的 `repo` 权限 |
| `GITHUB_PAGES_DOMAIN` | repo 的 Pages 域名，例：`https://yourname.github.io/your_clips_repo`         |
| `OPENAI_API_KEY`      | OpenAI（或代理）的 API key                                                   |
| `OPENAI_BASE_URL`     | 默认 `https://api.openai.com/v1`，用代理就改                                 |
| `OPENAI_MODEL`        | 推荐 `gpt-4o-mini`，省钱够用                                                 |

### 3.3 可选

| 变量                                  | 用途 |
| ------------------------------------- | ---- |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | 通知 |

复制并填写：

```bash
cp .env.example .env
$EDITOR .env
```

## 4. 第一次启动（FNS 还没 token，先跑起来拿 token）

```bash
docker compose up -d
docker compose logs -f fast-note-sync-service
```

第一次启动时 fast-note-sync 会引导你创建管理员账号。打开浏览器访问：

```
https://sync.example.com
```

按提示走完初始化，进入后台 → "Copy API Configuration" → 复制 token。

> ⚠️ 第一次访问 `sync.example.com` 时 Traefik 还在签证书，可能需要等 30~60 秒。
> 如果一直 502，先 `docker compose logs traefik` 看 ACME 状态。

## 5. 把 FNS_TOKEN 填回 .env，重启 web_clipper

```bash
$EDITOR .env       # 把 FNS_TOKEN=... 填上
docker compose up -d web_clipper
```

## 6. 验收

```bash
KEY=<.env 里的 API_KEY>
DOMAIN=example.com

# 6.1 web_clipper 健康检查（vault_api 兼容端点）
curl -fSsL -H "Authorization: Bearer $KEY" https://$DOMAIN/api/

# 6.2 列出 vault 文件
curl -fSsL -H "Authorization: Bearer $KEY" https://$DOMAIN/api/vault/
```

## 7. 本机 Obsidian 接入

见 [obsidian-plugin.md](obsidian-plugin.md)。

## 8. 客户端接入

- 浏览器扩展：[browser-extension.md](browser-extension.md)

## 9. 维护

### 升级

```bash
git pull
docker compose pull           # 拉最新的 fast-note-sync 镜像
docker compose build          # 重建 web_clipper 镜像
docker compose up -d
```

### 备份

物理卷在 `./data/`：

```
data/
├── letsencrypt/        ← Traefik 证书（删了会重新签，但有 rate limit）
└── fns/
    ├── storage/        ← vault 文件（最重要）
    └── config/         ← FNS 配置 + SQLite
```

定期备份：

```bash
tar czf clipper-backup-$(date +%F).tar.gz data/
# 或者用 restic / rclone 推到 S3
```

fast-note-sync 自身也支持把 vault 增量打包推到 S3/R2/OSS，建议在它后台开起来。

### 查日志

```bash
docker compose logs -f web_clipper
docker compose logs -f fast-note-sync-service
docker compose logs -f traefik | grep -i acme
```

### 改 OpenAI 模型 / API key

改 `.env` 后：

```bash
docker compose up -d web_clipper
```

不需要 rebuild。
