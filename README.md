# obsidian-clipper-gateway

> 把"网页剪藏"统一收口到一台 VPS，
> 自动 AI 摘要 / 打标签 / 落进 Obsidian vault，
> 本机通过 fast-note-sync plugin 实时同步。

---

## 这是什么

一个部署在 VPS 上的剪藏 + 同步网关。它把以下三类输入统一汇入你的 Obsidian vault：

1. **浏览器 Web Clipper 扩展**（基于 SingleFile）—— 一键把网页打包成 HTML 上传
2. **AI 客户端**（Cursor / Claude Desktop / Cherry Studio）—— 通过 MCP SSE 读写笔记

所有路径最终都落到 [fast-note-sync-service](https://github.com/haierkeys/fast-note-sync-service) 管理的 vault，本机 Obsidian 通过 [fast-note-sync plugin](https://github.com/haierkeys/obsidian-fast-note-sync) 实时（毫秒级）拉取更新。

---

## 架构

```
                         浏览器扩展
                         (SingleFile)
                              │
                  POST /api/upload
                              │
                              ▼
                       ┌──────────────┐
                                  │   Traefik    │  TLS / Let's Encrypt
                                  └──────┬───────┘
                                         │
                                  ┌──────▼───────────────────────────┐
                                  │      web_clipper                 │
                                  │  ① /upload                       │
                                  │     GitHub Pages 快照            │
                                  │     Jina → Markdown              │
                                  │     OpenAI 摘要 + 标签           │
                                  │     → 写入 FNS                   │
                                  │                                  │
                                  └──────────────┬───────────────────┘
                                                 │ REST
                                                 ▼
                              ┌──────────────────────────────────┐
                              │  fast-note-sync-service          │
                              │                                  │
                              │  · 文件存储 + SQLite 历史         │
                              │  · S3/R2/WebDAV 备份              │
                              │  · WebSocket /api/user/sync ─────┼──→ 本机 Obsidian
                              │  · MCP /api/mcp/sse        ──────┼──→ Cursor/Claude
                              └──────────────────────────────────┘
```

详见 [docs/architecture.md](docs/architecture.md)。

---

## 快速开始

### 0. 前提

- 一台公网可达的 Linux VPS（≥ 1 GB 内存即可）
- 一个解析到 VPS 的域名，**两条 A/AAAA 记录**：
  - `example.com` → VPS IP
  - `sync.example.com` → VPS IP
- 装好 Docker + Docker Compose

### 1. 克隆并配置

```bash
git clone https://github.com/yefeng8771/obsidian-clipper-gateway.git
cd obsidian-clipper-gateway
cp .env.example .env

# 至少改这几个：DOMAIN / ACME_EMAIL / API_KEY / FNS_TOKEN
# 以及 GITHUB_* / OPENAI_API_KEY（如需用浏览器扩展剪藏）
$EDITOR .env
```

生成几个随机密钥：

```bash
echo "API_KEY=$(openssl rand -hex 32)"
echo "FNS_TOKEN=（去 fast-note-sync 后台 Copy API Configuration 拿）"
```

### 2. 启动

```bash
docker compose up -d
docker compose logs -f
```

首次启动 Traefik 会自动申请 Let's Encrypt 证书（约 30 秒）。

### 3. 在 fast-note-sync 后台建 token

```bash
docker compose logs fast-note-sync-service | grep -i "admin\|password\|token" | head
# 或者直接打开 https://sync.example.com 走 Web 引导流程
```

把生成的 token 填回 `.env` 的 `FNS_TOKEN`，然后 `docker compose up -d` 让 web_clipper 重读。

### 4. 验收三件事

```bash
KEY=<你的 API_KEY>
DOMAIN=example.com

# 状态
curl -H "Authorization: Bearer $KEY" https://$DOMAIN/api/

# 写一条笔记
curl -X PUT \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: text/markdown" \
  --data $'# Hello\n\n来自 obsidian-clipper-gateway' \
  https://$DOMAIN/api/vault/Inbox/test.md

# 列文件
curl -H "Authorization: Bearer $KEY" https://$DOMAIN/api/vault/
```

成功后，几百毫秒内本机 Obsidian 应能看到 `Inbox/test.md`（前提：fast-note-sync plugin 已配置好，见下文）。

### 5. 本机 Obsidian 接入

打开 Obsidian → Settings → Community plugins → Browse → 搜 **Fast Note Sync** → 安装并启用：

| 字段     | 填法                                    |
| -------- | --------------------------------------- |
| Endpoint | `https://sync.example.com`              |
| Token    | 同 `.env` 里的 `FNS_TOKEN`              |
| Vault    | `Inbox`（或你 `.env` 里的 `FNS_VAULT`） |

详见 [docs/obsidian-plugin.md](docs/obsidian-plugin.md)。

### 6. 浏览器扩展接入

如果你之前用过 goxofy 的 [SingleFile + web_clipper](https://github.com/goxofy/web_clipper) 流程，扩展那边只需改 endpoint：

| 字段         | 新值                              |
| ------------ | --------------------------------- |
| Upload URL   | `https://example.com/api/upload/` |
| Bearer Token | `.env` 里的 `API_KEY`             |

详见 [docs/browser-extension.md](docs/browser-extension.md)。

---

## 目录结构

```
obsidian-clipper-gateway/
├── README.md                  ← 本文
├── LICENSE                    ← MIT (覆盖本仓库自有的修改 / 新增部分)
├── ATTRIBUTION.md             ← 上游致谢与许可说明
├── docker-compose.yml
├── .env.example
├── app/                       ← web_clipper 服务（基于 goxofy/web_clipper 改造）
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py              ← 删 NOTION_*，加 FNS_*
│   ├── web_clipper.py         ← save_to_notion → save_to_fns
│   └── vault_api.py           ← 新增：Local REST API 兼容层
├── docs/
│   ├── architecture.md
│   ├── deploy.md
│   ├── browser-extension.md
│   ├── obsidian-plugin.md
│   ├── dataview-recipes.md
│   └── troubleshooting.md
├── examples/
│   └── dataview-clippings-index.md
└── .github/
    └── ISSUE_TEMPLATE/
        └── upstream-license-notice.md
```

---

## 替代了什么 / 没替代什么

| 上游原本的能力              | 本仓库的处理                                                                                                |
| --------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Notion 数据库做"剪藏目录"   | **删除**。改用 Obsidian + Dataview 在 frontmatter 上动态生成目录视图（[recipes](docs/dataview-recipes.md)） |
| GitHub Pages 托管 HTML 快照 | **保留**。剪藏的 HTML 仍然托管在 GitHub Pages，frontmatter 里有 `snapshot:` 字段                            |
| OpenAI 生成摘要 + 标签      | **保留**。落入 frontmatter                                                                                  |
| Telegram 通知               | **保留**。可选                                                                                              |
| 实时同步到本机 Obsidian     | **新增**。fast-note-sync 的 WebSocket plugin                                                                |

---

## 文档索引

- [架构](docs/architecture.md) —— 数据流 / 时序 / 关键决策
- [部署](docs/deploy.md) —— VPS 从零到跑通的完整流程
- [浏览器扩展接入](docs/browser-extension.md) —— SingleFile-based 扩展
- [本机 Obsidian 配置](docs/obsidian-plugin.md) —— fast-note-sync plugin
- [Dataview 食谱](docs/dataview-recipes.md) —— 替代 Notion 视图
- [疑难排查](docs/troubleshooting.md)

---

## 上游致谢

本仓库基于以下开源/公开项目改造或集成：

- [goxofy/web_clipper](https://github.com/goxofy/web_clipper) —— 剪藏管道与 GitHub Pages / OpenAI / Telegram 集成代码的来源
- [haierkeys/fast-note-sync-service](https://github.com/haierkeys/fast-note-sync-service) —— vault 后端
- [haierkeys/obsidian-fast-note-sync](https://github.com/haierkeys/obsidian-fast-note-sync) —— Obsidian 同步插件
- [coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) —— 兼容协议规范

详见 [ATTRIBUTION.md](ATTRIBUTION.md)。

---

## License

本仓库自有的修改/新增部分按 [MIT](LICENSE) 授权。
上游 `goxofy/web_clipper` 代码部分**未声明许可证**，详见 [ATTRIBUTION.md](ATTRIBUTION.md)。
