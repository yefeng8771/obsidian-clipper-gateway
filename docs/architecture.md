# 架构

## 总览

```
浏览器扩展 (SingleFile) ─POST /api/upload─┐
userscript / 第三方     ─PUT  /api/vault/*─┤
AI 客户端 (MCP)        ─SSE  /api/mcp/sse─┤
                                          ▼
                                 ┌────────────────┐
                                 │    Traefik     │ TLS 终止
                                 └────────┬───────┘
                                 ┌────────▼───────┐
                                 │  web_clipper   │ ─── 8000
                                 │                │
                                 │  /upload       │ HTML → readability → AI → 写 FNS
                                 │  /vault/*      │ Local REST API 兼容透传
                                 └────────┬───────┘
                                          │ REST  http://fast-note-sync-service:9000
                                 ┌────────▼─────────────────────────┐
                                 │  fast-note-sync-service          │
                                 │                                  │
                                 │  · 文件存储（/storage）            │
                                 │  · SQLite 历史                    │
                                 │  · S3/R2/WebDAV 备份               │
                                 │  · WebSocket /api/user/sync       │  ──→ Obsidian plugin
                                 │  · MCP /api/mcp/sse               │  ──→ Cursor / Claude
                                 └──────────────────────────────────┘
```

## 端点路由

| 域名 | 路径 | 后端 | 用途 |
|---|---|---|---|
| `${DOMAIN}` | `/api/upload/*` | web_clipper:8000 | 浏览器扩展上传 SingleFile HTML |
| `${DOMAIN}` | `/api/vault/*`  | web_clipper:8000 | userscript 调 Local REST API 协议 |
| `${DOMAIN}` | `/api/`         | web_clipper:8000 | 健康检查（兼容 LRA） |
| `sync.${DOMAIN}` | 全部 | fast-note-sync:9000 | 本机 Obsidian plugin / MCP 客户端 |

Traefik 通过 docker label 自动发现 + Let's Encrypt 自动签证书。

## 数据流时序

### 浏览器扩展剪藏一篇文章

```
扩展 → POST /api/upload (HTML, original_url)
   ├─ web_clipper.upload_to_github     → 上传到 GitHub Pages，等待部署
   ├─ url2md (Jina r.jina.ai)           → 拿到结构化 markdown
   ├─ generate_summary_tags (OpenAI)    → 摘要 + 标签
   ├─ save_to_fns                       ┐
   │  └─ PUT https://sync.../api/note   │ → 落入 vault: Clippings/<slug>.md
   │     带 frontmatter: title/source/snapshot/summary/tags/clipped_at
   ├─ FNS WebSocket 推送                 → 本机 Obsidian 出现新文件
   └─ Telegram 通知（可选）
```

### userscript 写一条笔记

```
脚本 → PUT /api/vault/Linux.do/帖子标题.md (text/markdown)
   ├─ vault_api 验证 Bearer
   ├─ (可选) AI 富化 frontmatter
   ├─ POST /api/note 给 FNS
   └─ 204 返回
```

### userscript 上传图片

```
脚本 → PUT /api/vault/Linux.do/attachments/cat.png (image/png, 二进制)
   ├─ vault_api 识别为非 markdown
   ├─ POST /api/attachment 给 FNS（multipart）
   └─ 204 返回
```

## 关键决策

### 为什么 web_clipper 不再落本地盘

如果 web_clipper 同时写本地文件 + 写 FNS，两份数据会发生 split-brain：FNS 历史/同步只看自己存储里的版本。
统一让 FNS 当唯一存储，简单且无歧义。如果 FNS 临时不可用，web_clipper 直接 502 让客户端重试。

### 为什么 Notion 被替换

Notion 在原管道里干两件事：① 存元数据 ② 提供"剪藏目录"视图。
两件事都能在 Obsidian 内完成：
- 元数据 → frontmatter
- 目录视图 → Dataview 插件

少一个有状态服务、少一个 token，体验更内聚。详见 [dataview-recipes.md](dataview-recipes.md)。

### 为什么不需要 Syncthing

fast-note-sync-service 自带 WebSocket 推送，本机 Obsidian plugin 实时拉。Syncthing 在这里是多余的。
唯一例外：iOS 端如果不跑 fast-note-sync plugin，可以再叠 Möbius Sync 之类做底线。

### Traefik 还是 Caddy / nginx

任选其一，docker-compose 里改 labels 就行。Traefik 的优势是 docker label 自动发现 + 自动续签，
对这种"加一个服务就要加一组路由"的场景最省心。

## 容器与网络

| 容器 | 镜像 | 端口（容器内） | 网络 |
|---|---|---|---|
| `clipper-traefik` | `traefik:v3.1` | 80/443 | `edge` |
| `clipper-app` | 本仓库构建 | 8000 | `edge` + `internal` |
| `clipper-fns` | `haierkeys/fast-note-sync-service:latest` | 9000 | `edge` + `internal` |

`edge` 网络给 Traefik 暴露用；`internal` 网络让 web_clipper 和 fast-note-sync 直连
`http://fast-note-sync-service:9000`，不绕公网。

## 鉴权

- **`API_KEY`**：客户端（浏览器扩展、userscript、curl）→ web_clipper 的 Bearer
- **`FNS_TOKEN`**：web_clipper → fast-note-sync 的 Bearer
- **本机 Obsidian plugin token**：和 `FNS_TOKEN` 是同一个（fast-note-sync 后台生成）
- **MCP 客户端**：用 `FNS_TOKEN` 直接连 `https://sync.${DOMAIN}/api/mcp/sse`

两层 token 互不复用，出事可单独吊销。
