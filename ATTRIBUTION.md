# Attribution

## 上游来源（Upstream sources）

本仓库不是从零写起的。以下是每一块代码 / 镜像的来源与许可状况：

### 1. `app/web_clipper.py`、`app/main.py`、`app/config.py`、`app/Dockerfile`

- **来源**：[goxofy/web_clipper](https://github.com/goxofy/web_clipper)（master 分支，2025-02-10 创建）
- **本仓库的修改**：
  - 删除了 Notion 集成（`notion-client` 依赖、`save_to_notion` 方法、相关配置）
  - 新增了 `save_to_fns` —— 把剪藏写入 fast-note-sync-service
  - 在 `process_file` 流水线中用 FNS 替换 Notion 节点
  - 在 `web_clipper.py` 末尾挂载 `vault_api` 路由
  - 新增 `_safe_slug` / `_yaml_str` 两个 helper
- **上游许可证**：**未声明**（截至本仓库创建时间）。
  在 GitHub 上未声明 LICENSE 的代码，默认是 _All Rights Reserved_。
  本仓库的衍生使用基于以下两点：
  1. 上游公开发布在 GitHub 上，可视为对查阅与个人评估的默许；
  2. 我们已通过 issue 主动告知上游本派生仓库的存在（见
     [.github/ISSUE_TEMPLATE/upstream-license-notice.md](.github/ISSUE_TEMPLATE/upstream-license-notice.md)），
     若作者反对，本仓库会立即下架或重构去除上游代码。

### 2. `app/vault_api.py`

- **来源**：本仓库原创
- **遵循的协议**：[obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) 公开的 OpenAPI 规范（MIT 许可）。
  这里只保留了健康检查 (`/`) 和文件列表 (`/vault/`) 端点，`/vault/{path}` 读写删端点已移除。
- **许可证**：MIT（见根目录 LICENSE）

### 3. `docker-compose.yml` 中的 `fast-note-sync-service` 镜像

- **来源**：[haierkeys/fast-note-sync-service](https://github.com/haierkeys/fast-note-sync-service)（Apache-2.0）
- **使用方式**：仅以官方 Docker Hub 镜像 `haierkeys/fast-note-sync-service:latest` 引用，**不复制其源码**。

### 4. 浏览器扩展（参考集成）

- 上游 [goxofy/web_clipper](https://github.com/goxofy/web_clipper) 配套使用的是
  [SingleFile](https://github.com/gildas-lormeau/SingleFile)（AGPL）扩展。本仓库不分发此扩展。

### 5. userscript（参考集成）

- [Linux.do 帖子导出到 Obsidian](https://greasyfork.org/scripts/561785) —— 第三方公开脚本。
  本仓库不分发此脚本，仅提供 API 兼容层让其能指向本服务。

---

## 本仓库自有部分的许可证

除上述上游来源之外的全部内容（特别是 `vault_api.py` / `docker-compose.yml` / Traefik 配置 / `docs/*` / `README.md`）以 [MIT](LICENSE) 授权。

---

## 如果你是 goxofy

请见 [.github/ISSUE_TEMPLATE/upstream-license-notice.md](.github/ISSUE_TEMPLATE/upstream-license-notice.md)，或直接联系本仓库作者。
任何关于许可证 / 归属 / 下架的诉求都会被认真对待。
