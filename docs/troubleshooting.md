# 疑难排查

按现象找问题。每条都列出**首先看哪里 → 常见原因 → 怎么修**。

## 域名解析 / TLS

### 现象：浏览器打开 `https://example.com/api/` 显示 "证书无效" 或长时间 502

**首先看**：

```bash
docker compose logs traefik | grep -iE 'acme|error|certificate'
```

**常见原因**：

| 原因                                                | 修法                                                                                                                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DNS 还没生效                                        | `dig example.com` 看 A 记录是否指向 VPS                                                                                                                             |
| 80/443 端口没放行                                   | 云厂商安全组 + `ufw status` 检查                                                                                                                                    |
| Let's Encrypt rate limit（一周内反复销毁/重建会撞） | `data/letsencrypt/acme.json` 备份好，等 7 天，或暂时改用 staging：`--certificatesresolvers.le.acme.caserver=https://acme-staging-v02.api.letsencrypt.org/directory` |
| `ACME_EMAIL` 没填                                   | 改 `.env` 重启                                                                                                                                                      |
| `tlschallenge` 要求 80 端口直达 Traefik             | 检查 VPS 上是否有 nginx/apache 占着 80                                                                                                                              |

### 现象：`sync.example.com` 不通但 `example.com` 通

DNS 没解析 sync 子域。补上 A 记录指向同一个 IP，等几分钟。

## API 鉴权

### 现象：`curl /api/` 返回 `401 Invalid token`

| 原因                                       | 修法                                                 |
| ------------------------------------------ | ---------------------------------------------------- |
| Bearer 后忘了空格                          | `Authorization: Bearer <token>` 中间是空格，不是冒号 |
| Token 含特殊字符没引号                     | `curl -H "Authorization: Bearer $KEY"` 用双引号      |
| `.env` 改了 `API_KEY` 但没重启 web_clipper | `docker compose up -d web_clipper`                   |

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
4. **FNS 写入** —— 检查 `FNS_TOKEN` 和 `FNS_VAULT` 配置，看 fast-note-sync-service 日志

### 现象：剪藏的笔记里没有正文，只有空 frontmatter

通常是 Jina 转 markdown 失败、又 fallback 到 BeautifulSoup 也失败。
打开 frontmatter 里 `snapshot:` 那个 GitHub Pages URL 看一下原页面有没有内容——如果连原页面都是空的，那是网站 anti-scraping 导致 SingleFile 抓的是空骨架，不是 web_clipper 的锅。

## 资源 / 性能

### 现象：内存飙高 / OOM

`docker stats` 看哪个容器吃内存：

| 容器           | 正常范围                          |
| -------------- | --------------------------------- |
| traefik        | < 100 MB                          |
| web_clipper    | 150–400 MB（OpenAI 调用峰值会高） |
| fast-note-sync | 200–500 MB（取决于 vault 大小）   |

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
