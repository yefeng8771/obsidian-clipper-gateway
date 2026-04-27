# userscript 接入

适用于任何使用 [obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) 协议的 userscript / 自动化工具。
本文以 [Linux.do 帖子导出到 Obsidian](https://greasyfork.org/scripts/561785) 为例。

## 思路

- 脚本原本指向本机的 `https://127.0.0.1:27124`（Obsidian 插件）
- **改成指向你的 VPS**：`https://example.com/api`
- 不需要在本机安装 Obsidian Local REST API 插件
- 笔记会落到 fast-note-sync 的 vault → WebSocket 推到本机 Obsidian

## 步骤

### 1. 安装脚本

打开 https://greasyfork.org/scripts/561785 → "Install this script"。

### 2. 改脚本配置

打开油猴 / Tampermonkey → 找到这个脚本 → 设置（脚本一般会暴露 GUI 配置面板，
或者通过菜单命令打开）。

| 字段 | 改成 |
|---|---|
| API 地址（默认 `https://127.0.0.1:27124`） | **`https://example.com/api`** |
| API Key | **`.env` 里的 `API_KEY`**（不是 Obsidian 插件的 key） |
| 导出目录 | 保持默认 `Linux.do`，或改成你想要的子目录 |
| 图片目录 | 保持默认 `Linux.do/attachments` |
| 图片处理模式 | 推荐"保存图片并引用"（走 vault 附件接口） |

### 3. 测试一篇

随便打开一个 Linux.do 帖子，点脚本提供的"导出到 Obsidian"按钮。

预期：

- VPS 上 `docker compose logs web_clipper` 看到 PUT `/vault/Linux.do/<标题>.md` 的请求
- fast-note-sync 后台或 `data/fns/storage/` 出现新文件
- 本机 Obsidian 几百毫秒内出现这个文件

## 协议端点对照

vault_api 实现了以下端点（与 Local REST API 完全一致）：

| 方法 | 路径 | 行为 |
|---|---|---|
| GET  | `/` | 健康检查（脚本一般会 ping） |
| GET  | `/vault/` | 列文件 |
| GET  | `/vault/{path}` | 读文件（markdown 返回 text/markdown，二进制返回 octet-stream） |
| PUT  | `/vault/{path}` | 写/覆盖（markdown 或二进制） |
| POST | `/vault/{path}` | 文件存在则**追加 markdown**，不存在等价 PUT |
| DELETE | `/vault/{path}` | 删除 |

## 兼容其他 userscript / 工具

任何曾经写过 "把 X 保存到 Obsidian Local REST API" 的脚本都适用，比如：

- 微信文章 → Obsidian
- Twitter / X 收藏 → Obsidian
- RSS 订阅 → Obsidian

把 endpoint 改成 `https://example.com/api`，token 改成 `API_KEY`，就完事。

## 问答

### Q: 脚本里的"导出目录"和 .env 里的 `FNS_FOLDER` 关系是什么？

`FNS_FOLDER` 只影响 `/upload`（浏览器扩展剪藏）的落点。
脚本通过 `/vault/{path}` 写入时，路径完全由脚本控制，VPS 侧不会再加前缀。

### Q: 想给脚本写入的笔记自动加 AI 摘要 / 标签？

`.env` 里：

```bash
VAULT_AI_ENRICH=true
```

然后 `docker compose up -d web_clipper`。
注意：每条笔记都会调一次 OpenAI，**会花钱**。脚本本身已经做了结构化（提取楼主、回复等）的话不必开。

### Q: 想看每条笔记什么时候写进来？

`.env` 里：

```bash
VAULT_NOTIFY=true
TELEGRAM_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<your chat id>
```

每次 vault 写入会发一条简短通知。
