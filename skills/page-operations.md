# page-operations skill

## pageId 规则

当前页面 ID 使用数据库页面主键派生出的 `page-{id}` 形式，例如：

- `page-1`
- `page-2`
- `page-3`

这是当前数据库记录对应的业务页面 ID。页面关闭或窗口失效后，旧 `pageId` 不应继续当作可操作页面使用。

## 页面定位优先级

- 传 `pageId`：优先按 `pageId`。
- 否则传 `urlContains`：按 URL 模糊匹配。
- 都不传：默认取当前 active / 最近页面。

## 当前 active 页来源

以下操作会更新 active page：

- 新建标签页。
- 打开 URL 且 `bringToFront=true`。
- 接管页面。
- 激活页面。
- 关闭 active 页面后重新同步剩余页面状态。

## 相关接口

默认带 `/auto-download` 前缀：

- `POST /browser/tab/open`
- `POST /browser/page/open-url`
- `POST /browser/page/batch-open-config`
- `GET /browser/pages`
- `GET /browser/page-info`
- `POST /browser/page/activate`
- `POST /browser/page/close`
- `GET /browser/takeover/page-info`

## 适用场景

适合在列表页后立即激活、查询或关闭目标页。若后续需要跨窗口、跨进程、跨时间的稳定标识，需要升级页面标识策略，并同步数据库表和文档。

## Batch configured pages

`POST /browser/page/batch-open-config` reads `ad_browser_page_config` by `configCode`, opens only `status='1'` rows ordered by `sort_no,id`, and records the opened runtime pages in `ad_browser_page`.
