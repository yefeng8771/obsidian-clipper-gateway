# 本机 Obsidian 接入

通过 [fast-note-sync plugin](https://github.com/haierkeys/obsidian-fast-note-sync) 把本机 Obsidian 和 VPS 的 vault 双向实时同步。

## 1. 安装插件

Obsidian → Settings → Community plugins → **Turn on community plugins**（如果还没开）→ Browse → 搜 "**Fast Note Sync**" → Install → Enable。

如果商店里搜不到：

1. 下载 release：https://github.com/haierkeys/obsidian-fast-note-sync/releases
2. 解压到本地 vault 的 `.obsidian/plugins/fast-note-sync/`
3. 重启 Obsidian → Settings → Community plugins → Reload → Enable

## 2. 配置插件

打开插件设置：

| 字段 | 填法 |
|---|---|
| Endpoint | `https://sync.example.com` |
| Token | `.env` 里的 `FNS_TOKEN`（同一个 token） |
| Vault | `Inbox`（或你 `.env` 里的 `FNS_VAULT`） |
| Auto sync | 推荐开 |
| Sync attachments | 推荐开 |

> 部分版本可能要求一次性粘贴一段"远程服务配置"——它就是把上面几条 JSON 化的写法。
> 后台 "Copy API Configuration" 复制出来直接粘即可。

## 3. 第一次同步

插件会把 VPS 上 vault 的全部内容拉到本地。**如果本机 vault 已经有同名文件，会按时间戳合并**，但建议在小测试 vault 里先跑一遍。

## 4. 验证实时性

```bash
# VPS 端写一条笔记
KEY=<API_KEY>
curl -X PUT \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: text/markdown" \
  --data $'# WebSocket 推送测试' \
  https://example.com/api/vault/Inbox/ws-test.md
```

本机 Obsidian 文件树应该几百毫秒内出现 `Inbox/ws-test.md`。

## 5. 移动端

Obsidian 移动版（iOS / Android）也能装 fast-note-sync plugin。配置同上。

> iOS 偶尔有插件兼容性问题。如果 plugin 跑不起来，备选方案是把 vault 目录用
> Möbius Sync / iSH 之类的同步到 fast-note-sync 的 `data/fns/storage/`，
> 但这绕过了 plugin 的 history/冲突合并能力，**不推荐作为主路径**。

## 6. 给 AI 客户端开 MCP

fast-note-sync 自带 MCP SSE 端点：

```
https://sync.example.com/api/mcp/sse
```

带上 `Authorization: Bearer <FNS_TOKEN>` header。

### Cursor / Claude Desktop / Cherry Studio

在它们的 MCP servers 配置里加一条：

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "url": "https://sync.example.com/api/mcp/sse",
      "headers": {
        "Authorization": "Bearer <FNS_TOKEN>"
      }
    }
  }
}
```

之后可以在 Cursor / Claude 里直接让 AI 读写笔记，比如：

> "把我 Inbox/Clippings 下面所有 tag 包含 #react 的笔记找出来做摘要"

## 故障排查

### 同步不动

1. 浏览器开 `https://sync.example.com` 能不能进后台 → 不能就先看 Traefik / FNS 日志
2. plugin 那边的 token 是不是和 VPS 上的 `FNS_TOKEN` 完全一致
3. plugin 设置里的 vault 名是不是和 `FNS_VAULT` 一致
4. 浏览器 devtools 里看 WS 连接：插件应该建立到 `wss://sync.example.com/api/user/sync`

### Traefik 把 WebSocket 打断了

这通常是装了 gzip / response buffering middleware 导致的。本仓库的 `docker-compose.yml`
**没有**给 `sync.${DOMAIN}` 路由加任何中间件，理论上不会有问题。
如果你自己改了 Traefik 配置加了 middleware，记得排除掉 sync 域名。
