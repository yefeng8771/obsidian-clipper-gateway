---
name: 上游告知模板（提交到 goxofy/web_clipper）
about: 用于知会上游作者本仓库基于其代码做了衍生
title: "[Notice] Derivative work at yefeng8771/obsidian-clipper-gateway"
labels: ""
assignees: ""
---

Hi @goxofy,

感谢你开源了 [web_clipper](https://github.com/goxofy/web_clipper) —— 它的 SingleFile + GitHub Pages + AI 摘要的设计帮我省了非常多重复劳动。

我基于它做了一个面向 Obsidian 用户的衍生项目：

**仓库**：https://github.com/yefeng8771/obsidian-clipper-gateway

**主要改动**：
1. 删除了 Notion 集成（依赖、`save_to_notion`、相关配置）
2. 新增 `save_to_fns` —— 把剪藏写入 [fast-note-sync-service](https://github.com/haierkeys/fast-note-sync-service)
3. 新增 `vault_api.py` —— 对外暴露 [obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) 协议的兼容层，让现成的 userscript（如 greasyfork/561785）无需安装本机 Obsidian Local REST API 插件即可使用
4. 重写 docker-compose 把 web_clipper + fast-note-sync-service + Traefik 拼成一键部署栈
5. 补齐了完整中文文档

**致谢**：核心剪藏管道（GitHub Pages 上传、Jina2MD、OpenAI 摘要、Telegram 通知、文件名解析等）来自你的代码，已在 README 和 ATTRIBUTION.md 中显著标注。

**关于许可证**：注意到 web_clipper 仓库未声明 LICENSE，按 GitHub 默认即 *All Rights Reserved*。我已经在 README/ATTRIBUTION 里说明了这一点，并把派生仓库设为 Public 是为了让其它有相同需求的用户能找到。

**如果你**：
- 不希望我们继续派生 → 请回复，我会立即把仓库下架或重构去除上游代码；
- 愿意补一个 LICENSE（如 MIT/Apache-2.0/AGPL）→ 那再好不过，我们会按你的选择更新归属说明；
- 觉得没问题 → 也欢迎你来 obsidian-clipper-gateway 提 issue/PR，把改动反向回馈或一起讨论。

感谢你的工作 🙏

—— @yefeng8771
