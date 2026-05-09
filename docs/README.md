# docs

项目技术文档目录，存放架构说明、开发指南、API 调用链、依赖关系等详细文档。

## 文档索引

| 文档 | 说明 | 目标读者 |
|------|------|---------|
| [architecture.md](architecture.md) | 项目分层、模块职责、调用链路、数据模型、路由前缀、异常处理 | 新加入开发者、架构评审 |
| [key-classes-functions.md](key-classes-functions.md) | 核心类、函数、API 端点详细参考 | 开发时查阅具体类和方法签名 |
| [dependency-graph.md](dependency-graph.md) | 外部/内部依赖、数据流、线程模型 | 排查依赖冲突、理解运行时行为 |
| [api-call-chain.md](api-call-chain.md) | 接口到 schema、service、manager、数据库/外部依赖的映射 | 新增接口时确定改动范围 |
| [development-guide.md](development-guide.md) | 新增能力时的固定改动顺序和约束 | 开发新功能前的必读指南 |
| [rpa-common-methods.md](rpa-common-methods.md) | RPA 公共方法层详细说明（页面/DOM/图像/鼠标/键盘/数据/等待/断言/流程编排） | 使用或扩展 RPA 能力 |

## 阅读顺序建议

### 新开发者入门

1. [architecture.md](architecture.md) — 理解项目整体架构和分层
2. [development-guide.md](development-guide.md) — 了解开发约束和扩展顺序
3. [api-call-chain.md](api-call-chain.md) — 熟悉接口映射关系
4. [key-classes-functions.md](key-classes-functions.md) — 查阅核心类和方法

### 新增功能时

1. [development-guide.md](development-guide.md) — 确定改动顺序
2. [api-call-chain.md](api-call-chain.md) — 确定需要修改的接口和映射
3. [dependency-graph.md](dependency-graph.md) — 确认依赖影响范围
4. 开发完成后更新 [architecture.md](architecture.md) 和 [key-classes-functions.md](key-classes-functions.md)

### 问题排查时

- **接口行为异常** → [api-call-chain.md](api-call-chain.md) + [key-classes-functions.md](key-classes-functions.md)
- **依赖/环境问题** → [dependency-graph.md](dependency-graph.md)
- **页面定位问题** → `../skills/page-operations.md`
- **图像点击问题** → `../skills/visual-service.md` + `../skills/business-image-click.md`
- **浏览器启动问题** → `../skills/browser-service.md`

## 与 skills 目录的关系

| 目录 | 内容侧重 | 更新频率 |
|------|---------|---------|
| `docs/` | 技术架构、接口映射、开发规范、详细参考 | 架构变更时更新 |
| `skills/` | 按功能模块拆分的能力说明、快速导航、最佳实践 | 功能迭代时更新 |

`docs/` 文档更偏向"技术参考手册"，`skills/` 文档更偏向"能力使用指南"。两者互补，共同构成项目完整文档体系。

## 相关入口

- 项目总纲/技能树：`../SKILL.md`
- 项目入口/快速启动：`../README.md`
- 代理规则/约束：`../AGENT.md`
- 能力使用指南：`../skills/README.md`
