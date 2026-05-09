# skills

本目录存放给后续维护者或自动化代理使用的能力说明。详细架构和接口调用链见：

- `../docs/architecture.md`
- `../docs/api-call-chain.md`
- `../docs/development-guide.md`
- `../docs/rpa-common-methods.md`

当前项目不是 Vue + Java 后端结构；没有 Vue 页面、controller、mapper/xml。对应关系见 `../README.md`。

## 能力文档索引

| 文档 | 说明 | 适用场景 |
|------|------|---------|
| [browser-service.md](browser-service.md) | 浏览器 service / API / manager / 数据库的关系 | 新增浏览器能力、调试窗口/页面生命周期 |
| [page-operations.md](page-operations.md) | 标签页与页面定位规则 | 页面定位异常、理解 pageId 规则 |
| [desktop-service.md](desktop-service.md) | 桌面窗口、键盘、窗口激活扩展说明 | 新增桌面能力、窗口激活问题排查 |
| [visual-service.md](visual-service.md) | 坐标点击、模板图点击与 OCR 预留说明 | 图像点击失败排查、新增视觉能力 |
| [business-image-click.md](business-image-click.md) | 业务公共图像点击服务 | 业务流程图像点击逻辑调整 |
| [rpa-common-methods.md](rpa-common-methods.md) | RPA 公共方法层完整说明 | 新增 RPA 动作、流程编排、影刀类能力扩展 |
| [commit-rules.md](commit-rules.md) | PR 提交规范 | 代码提交、PR 创建 |

## 快速导航

### 按功能模块

- **浏览器自动化** → [browser-service.md](browser-service.md) + [page-operations.md](page-operations.md)
- **桌面窗口自动化** → [desktop-service.md](desktop-service.md)
- **图像/屏幕自动化** → [visual-service.md](visual-service.md) + [business-image-click.md](business-image-click.md)
- **RPA 公共方法** → [rpa-common-methods.md](rpa-common-methods.md)
- **业务流程编排** → [business-image-click.md](business-image-click.md) + [rpa-common-methods.md](rpa-common-methods.md)

### 按开发阶段

- **新增能力前** → [commit-rules.md](commit-rules.md)（提交规范）
- **新增浏览器能力** → [browser-service.md](browser-service.md)
- **新增桌面/图像能力** → [desktop-service.md](desktop-service.md) / [visual-service.md](visual-service.md)
- **新增 RPA 动作** → [rpa-common-methods.md](rpa-common-methods.md)
- **调整业务流程** → [business-image-click.md](business-image-click.md)
- **页面定位问题** → [page-operations.md](page-operations.md)
