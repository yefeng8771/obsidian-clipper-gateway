# 疑难排查

按现象找问题。每条都列出**首先看哪里 → 常见原因 → 怎么修**。

## 域名解析 / TLS

### 现象：浏览器打开 `https://example.com/api/` 显示 "证书无效" 或长时间 502

**首先看**：

```bash
docker compose logs traefik | grep -iE 'acme|error|certificate'
```

**常见原因**：

| 原因 | 修法 |
|---|---|
| DNS 还没生效 | `dig example.com` 看 A 记录是否指向 VPS |
| 80/443 端口没放行 | 云厂商安全组 + `ufw status` 检查 |
| Let's Encrypt rate limit（一周内反复销毁/重建会撞） | `data/letsencrypt/acme.json` 备份好，等 7 天，或暂时改用 staging：`--certificatesresolvers.le.acme.caserver=https://acme-staging-v02.api.letsencrypt.org/directory` |
| `ACME_EMAIL` 没填 | 改 `.env` 重启 |
| `tlschallenge` 要求 80 端口直达 Traefik | 检查 VPS 上是否有 nginx/apache 占着 80 |

### 现象：`sync.example.com` 不通但 `example.com` 通

DNS 没解析 sync 子域。补上 A 记录指向同一个 IP，等几分钟。

## API 鉴权

### 现象：`curl /api/` 返回 `401 Invalid token`

| 原因 | 修法 |
|---|---|
| Bearer 后忘了空格 | `Authorization: Bearer <token>` 中间是空格，不是冒号 |
| Token 含特殊字符没引号 | `curl -H "Authorization: Bearer $KEY"` 用双引号 |
| `.env` 改了 `API_KEY` 但没重启 web_clipper | `docker compose up -d web_clipper` |

### 现象：`curl /api/vault/foo.md` 写入返回 `502 fast-note-sync 写入失败`

**首先看**：

```bash
docker compose logs web_clipper | tail -50
docker compose logs fast-note-sync-service | tail -50
```

| 原因 | 修法 |
|---|---|
| `FNS_TOKEN` 未配置 / 错的 | 进 `https://sync.example.com` 后台重新 Copy API Configuration |
| `FNS_VAULT` 不存在 | 在 fast-note-sync 后台先建 vault，或改 `.env` 用现有的 |
| FNS 服务挂了 | `docker compose restart fast-note-sync-service` |
| FNS 端点路径不一致（不同版本字段名可能微调） | `curl https://sync.example.com/swagger` 看实际 schema，对照 `vault_api.py` 里 `/api/note` `/api/attachment` 的请求体调整 |

## userscript 相关

### 现象：脚本提示"连接失败"或 CORS 错误

userscript 一般用 `GM_xmlhttpRequest`（不受 CORS 约束）。如果脚本改用 `fetch` 触发 CORS：

在 `app/web_clipper.py` 的 `app = FastAPI()` 之后加：

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 或精确到脚本运行的网站
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`docker compose build web_clipper && docker compose up -d web_clipper`。

### 现象：脚本写入成功但本机 Obsidian 没收到

按顺序排查：

1. `data/fns/storage/<vault>/...` 物理文件是否存在
   - 不存在 → 看 web_clipper 日志确认是不是 FNS 写失败被吞
   - 存在 → 问题在 plugin 端
2. plugin token / endpoint / vault 名是否和 VPS 一致
3. plugin 那侧的 WS 连接：浏览器版 Obsidian 可以开 devtools 看 Network。桌面版可以 `Ctrl+Shift+I` 同样看
4. fast-note-sync plugin 重新点一次 "Sync now"

### 现象：图片上传失败（PUT /vault/.../attachments/x.png 返回 500）

`docker compose logs web_clipper | grep -i attach` 看具体报错。
最常见的是 fast-note-sync 的附件接口字段名差异：

```python
# vault_api.py 里 _write_to_fns 的非 markdown 分支
files={"file": (Path(filepath).name, body, ctype)}
data={"vault": FNS_VAULT, "path": filepath}
```

不同版本可能要求 `attachment_path` / `name` 之类的字段。`curl https://sync.example.com/swagger` 对照实际定义。

## 浏览器扩展剪藏

### 现象：`/upload/` 返回 200 但没有 obsidian_url

看日志：

```bash
docker compose logs web_clipper | grep -E 'GitHub|Jina|OpenAI|FNS'
```

依次定位是哪一步失败：

1. **GitHub 上传** —— token 权限 / repo 名错
2. **Jina r.jina.ai** —— 偶发不稳，会自动重试 30 次；如果一直失败，会 fallback 到 BeautifulSoup
3. **OpenAI** —— `OPENAI_BASE_URL` / `OPENAI_API_KEY` 错；或国内网络要走代理
4. **FNS 写入** —— 同上"`502 fast-note-sync 写入失败`"那一节

### 现象：剪藏的笔记里没有正文，只有空 frontmatter

通常是 Jina 转 markdown 失败、又 fallback 到 BeautifulSoup 也失败。
打开 frontmatter 里 `snapshot:` 那个 GitHub Pages URL 看一下原页面有没有内容——如果连原页面都是空的，那是网站 anti-scraping 导致 SingleFile 抓的是空骨架，不是 web_clipper 的锅。

## 资源 / 性能

### 现象：内存飙高 / OOM

`docker stats` 看哪个容器吃内存：

| 容器 | 正常范围 |
|---|---|
| traefik | < 100 MB |
| web_clipper | 150–400 MB（OpenAI 调用峰值会高） |
| fast-note-sync | 200–500 MB（取决于 vault 大小） |

如果 web_clipper 吃掉超过 1 GB 通常是某次 SingleFile HTML 文件特别大。`MAX_FILE_SIZE` 默认 30MB，建议保持。

### 现象：磁盘塞满

```bash
du -sh data/*
```

通常是 `data/fns/storage/`（vault 文件）。在 fast-note-sync 后台开一个 S3/R2 备份并清理本地历史。
另外 `data/letsencrypt/acme.json` 一般 < 100 KB，正常情况下不会大。

## 升级 / 回滚

### 现象：`docker compose pull` 后 fast-note-sync 起不来

新版本可能改了 schema，`data/fns/config/` 里的 SQLite 不兼容。**回滚**：

```yaml
# docker-compose.yml 里把镜像 tag 锁死到上一个版本
image: haierkeys/fast-note-sync-service:v1.2.3
```

```bash
docker compose up -d
```

平时建议在 `.env` 之外维护一个版本锁定的 `docker-compose.override.yml`。

## 调试工具

```bash
# 进容器看
docker compose exec web_clipper sh
docker compose exec fast-note-sync-service sh

# Traefik dashboard（默认未开放，按需启用）
# 在 traefik command 里加：
#   --api.insecure=true
#   --api.dashboard=true
# 然后用 ssh tunnel：
#   ssh -L 8080:localhost:8080 vps
# 浏览器开 http://localhost:8080
```

如果按这份文档还是搞不定，欢迎在仓库提 issue，附上：

1. `docker compose ps`
2. `docker compose logs --tail 100 <服务>`
3. 你做了什么操作触发的
