# Dataview 食谱：用 Obsidian 替代 Notion 视图

Notion 在原管道里干的事是"剪藏库目录"——一个能筛选、排序、按 tag 分组的视图。
Obsidian + [Dataview](https://github.com/blacksmithgu/obsidian-dataview) 插件能在 markdown 内部完成同样的事，
而且数据源就是你笔记的 frontmatter，无需另一份数据库。

## 0. 装 Dataview

Settings → Community plugins → Browse → 搜 "**Dataview**" → Install → Enable。
建议在插件设置里打开 **Enable JavaScript Queries**（dataviewjs 更强）。

## 1. 全部剪藏，按时间倒序

新建一个笔记 `Clippings/_Index.md`：

````markdown
# 剪藏库

```dataview
TABLE
  source        AS "原始链接",
  summary       AS "摘要",
  tags
FROM "Clippings"
WHERE source != null
SORT clipped_at DESC
```
````

效果就是一个 Notion 表格视图，自动包含整个 `Clippings/` 目录下的笔记。

## 2. 按月份分组

````markdown
```dataview
TABLE WITHOUT ID
  file.link      AS "标题",
  summary,
  tags
FROM "Clippings"
GROUP BY dateformat(date(clipped_at), "yyyy-MM") AS "月份"
SORT 月份 DESC
```
````

## 3. 只看包含某个 tag 的剪藏

````markdown
```dataview
TABLE source, summary
FROM "Clippings"
WHERE contains(tags, "AI") OR contains(tags, "machine-learning")
SORT clipped_at DESC
```
````

## 4. 全文检索摘要

````markdown
```dataview
LIST summary
FROM "Clippings"
WHERE contains(lower(summary), lower("Postgres"))
```
````

## 5. 仪表盘：每天剪了几篇

新建 `Dashboard.md`，用 dataviewjs：

````markdown
```dataviewjs
const pages = dv.pages('"Clippings"').where(p => p.clipped_at);
const byDay = {};
for (const p of pages) {
  const day = p.clipped_at.toISODate();
  byDay[day] = (byDay[day] || 0) + 1;
}
const rows = Object.entries(byDay)
  .sort((a, b) => b[0].localeCompare(a[0]))
  .slice(0, 30);
dv.table(["日期", "数量"], rows);
```
````

## 6. 标签云

````markdown
```dataviewjs
const counts = {};
for (const p of dv.pages('"Clippings"')) {
  for (const t of (p.tags || [])) counts[t] = (counts[t] || 0) + 1;
}
const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
dv.table(["Tag", "次数"], sorted);
```
````

## 7. 来源域名 Top 10

````markdown
```dataviewjs
const counts = {};
for (const p of dv.pages('"Clippings"').where(p => p.source)) {
  try {
    const host = new URL(p.source).hostname;
    counts[host] = (counts[host] || 0) + 1;
  } catch {}
}
const top = Object.entries(counts)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10);
dv.table(["域名", "数量"], top);
```
````

## 8. 待整理（无标签）的剪藏

````markdown
```dataview
LIST source
FROM "Clippings"
WHERE !tags OR length(tags) = 0
SORT clipped_at DESC
LIMIT 50
```
````

## 9. 一周回顾

````markdown
```dataview
TABLE source, summary, tags
FROM "Clippings"
WHERE clipped_at >= date(today) - dur(7 days)
SORT clipped_at DESC
```
````

## 10. 与外部分享：导出剪藏目录为 markdown 表格

把第 1 条食谱的查询结果用 Dataview 的 "Copy as markdown" 功能复制出来，就能粘到 GitHub README、博客、Slack 里——比 Notion 的 publish 链接更轻。

---

## 进阶：把 frontmatter 变成"准数据库"

Dataview 不止能查 frontmatter，还能把 inline 字段当作数据：

```markdown
---
status: read
priority:: 3
---

# 标题
```

````markdown
```dataview
TABLE status, priority
FROM "Clippings"
WHERE priority >= 3 AND status = "read"
SORT priority DESC
```
````

适合做"剪藏的下一步行动"管理：标记为待读 / 已读 / 待写笔记。
