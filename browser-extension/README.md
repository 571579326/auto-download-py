# browser-extension

本目录是未来 Chrome 扩展版本的预留目录，不是当前 Vue 前端目录。

当前仓库没有实际前端页面。后续如果新增 Vue、React 或 Chrome 扩展界面，应通过 FastAPI HTTP API 调用后端能力，默认接口前缀为 `/auto-download`。

后续扩展方向：

- tabs / windows / tabGroups 采集。
- 页面工作区快照上报。
- 浏览器恢复任务轮询。
- 分组恢复。
- 对 `app/api/browser.py` 和 `app/api/desktop.py` 的 HTTP 调用封装。

调用链应保持：

```text
Chrome 扩展或未来前端
  -> /auto-download/** HTTP API
  -> app/api/*.py
  -> app/services/*.py
  -> manager/runtime 层
```
