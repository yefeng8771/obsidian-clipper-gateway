# 剪藏库

> 本文件可以直接放到你的 Obsidian vault 里（建议放 `Clippings/_Index.md`）。

## 全部剪藏

```dataview
TABLE
  source        AS "原始链接",
  summary       AS "摘要",
  tags
FROM "Clippings"
WHERE source != null
SORT clipped_at DESC
```

## 按月分组

```dataview
TABLE WITHOUT ID
  file.link AS "标题",
  summary,
  tags
FROM "Clippings"
GROUP BY dateformat(date(clipped_at), "yyyy-MM") AS "月份"
SORT 月份 DESC
```

## 来源 Top 10

```dataviewjs
const counts = {};
for (const p of dv.pages('"Clippings"').where(p => p.source)) {
  try {
    const host = new URL(p.source).hostname;
    counts[host] = (counts[host] || 0) + 1;
  } catch {}
}
const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
dv.table(["域名", "数量"], top);
```

## 待整理（无标签）

```dataview
LIST source
FROM "Clippings"
WHERE !tags OR length(tags) = 0
SORT clipped_at DESC
LIMIT 50
```

更多查询见 [docs/dataview-recipes.md](../docs/dataview-recipes.md)。
