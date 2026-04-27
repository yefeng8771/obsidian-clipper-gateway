# 浏览器扩展接入

上游 [goxofy/web_clipper](https://github.com/goxofy/web_clipper) 配套的剪藏扩展是
[SingleFile](https://github.com/gildas-lormeau/SingleFile)。它的工作机制：

1. 访问任意网页 → 点扩展按钮
2. SingleFile 把页面打包成单个自包含 HTML（含图片 base64）
3. 通过扩展配置的"Upload to URL"功能 POST 到我们的 `/api/upload/`
4. web_clipper 走完整流水线：GitHub Pages 快照 → Jina2MD → OpenAI 摘要 → 写入 vault → Telegram 通知

## 1. 安装 SingleFile

| 浏览器 | 链接 |
|---|---|
| Chrome | https://chrome.google.com/webstore/detail/singlefile/mpiodijhokgodhhofbcjdecpffjipkle |
| Firefox | https://addons.mozilla.org/firefox/addon/single-file/ |
| Edge | https://microsoftedge.microsoft.com/addons/detail/singlefile/efnbkdcfmcmnhlkaijjjmhjjgladedno |

## 2. 配置 SingleFile 上传到本服务

打开扩展设置 → **Destination** 标签页：

| 字段 | 值 |
|---|---|
| Save to: | `URL` |
| Upload URL | `https://example.com/api/upload/` |
| Authorization Token | `Bearer <你的 API_KEY>` |
| Field name | `singlehtmlfile` |
| Method | `POST` |

> 不同版本的 SingleFile 字段名可能略有差异，关键是：
> - URL 要以 `/api/upload/` 结尾（注意结尾的 `/`）
> - Authorization 头要带 `Bearer ` 前缀
> - 表单字段名必须是 `singlehtmlfile`

## 3. 配置原始 URL 字段

web_clipper 期望表单中带一个 `url` 字段（原网页 URL）。
SingleFile 高级版本支持自定义 form fields，加一条：

| name | value |
|---|---|
| `url` | `{url}` 或 SingleFile 模板里代表当前页面 URL 的占位符 |

如果用的是不支持自定义字段的版本，web_clipper 也会从文件名（SingleFile 把 URL 编码进文件名）反解。

## 4. 测试

点扩展按钮剪一篇文章。预期：

```
docker compose logs -f web_clipper
```

看到：

```
🔄 开始处理新的网页剪藏...
📤 GitHub 上传成功: https://your.github.io/.../clips/xxx.html
📑 页面标题: ...
📝 摘要: ...
🏷️ 标签: ...
📒 Obsidian 保存成功: obsidian://open?vault=Inbox&file=Clippings/xxx.md
✨ 网页剪藏处理完成!
```

本机 Obsidian 在 `Clippings/` 出现新文件，frontmatter 类似：

```yaml
---
title: "页面原标题"
source: https://原网页.com/article
snapshot: https://your.github.io/repo/clips/xxx.html
summary: "AI 生成的摘要"
tags: ["tag1", "tag2", "tag3"]
clipped_at: 2026-04-27T12:34:56+00:00
---
```

## 5. 自定义剪藏落点

`.env` 改：

```bash
FNS_FOLDER=Clippings/Tech     # 落到子目录
FNS_VAULT=Inbox               # 或者完全独立的 vault
```

```bash
docker compose up -d web_clipper
```

## 6. 不想要 GitHub Pages 快照？

如果不在意"原页面挂了仍能看"，只想要 markdown 进 vault，可以把
`GITHUB_REPO` / `GITHUB_TOKEN` 留空。但这样 `process_file` 会失败（上游代码强依赖 GitHub）。

**当前版本不支持跳过 GitHub 步骤**。要支持的话需要再做一个轻量分支：HTML → 直接 readability 转 markdown → 写 vault，跳过 Pages。
如果你需要这个能力，欢迎提 issue 或 PR。
