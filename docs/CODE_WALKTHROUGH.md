# TaskFlow API 代码走读与面试讲解

这份文档用于第二阶段学习：项目已经能启动、能在 `/demo` 操作台走通之后，开始理解代码为什么这样写。不要一次读完全部内容。每一节都按“先运行、再读代码、最后回答问题”的顺序完成。

## 学习前准备

在项目根目录双击 `start_taskflow.bat`，确认服务运行正常。然后打开：

```text
http://127.0.0.1:8000/demo
```

如果端口不是 8000，以启动窗口显示的地址为准。

每一节结束后都要能回答检查点问题。回答不出来时，先回到对应代码，不要继续背下面的内容。

## 一次请求到底经过什么

以“已登录用户创建任务”为例：

```text
浏览器或 HTTP 客户端
        |
        | POST /api/v1/projects/1/tasks
        | Authorization: Bearer <JWT>
        v
FastAPI Router
        |
        | 解析 JSON -> TaskCreate
        | 校验 JWT -> CurrentUser
        | 查询项目并校验 owner_id -> OwnedProject
        v
业务函数 create_task
        |
        | 创建 SQLAlchemy Task 对象
        | add + commit + refresh
        v
SQLite 或 PostgreSQL
        |
        | 返回 Task 模型
        v
TaskRead 转换为 JSON，HTTP 201
```

需要记住六层职责：

| 层 | 文件位置 | 只负责什么 |
| --- | --- | --- |
| Route | `src/taskflow/api/routes/` | HTTP 路径、状态码、业务流程 |
| Dependency | `src/taskflow/api/dependencies.py` | 身份校验、资源所有权校验 |
| Schema | `src/taskflow/schemas/` | 输入校验、输出结构 |
| Model | `src/taskflow/models/` | 数据库表和关系 |
| Security | `src/taskflow/security.py` | 密码哈希、JWT 签发和校验 |
| Database | `src/taskflow/database.py` | Engine、Session、Base、建表 |

## 第 1 节：注册、密码和登录

先打开 `src/taskflow/api/routes/auth.py`，再看 `src/taskflow/security.py`。

注册请求进入 `register_user` 后依次发生：

1. FastAPI 先按 `UserCreate` 校验邮箱、姓名和密码长度。不合法时直接返回 422，业务函数不会执行。
2. `payload.email.lower()` 把邮箱统一成小写，避免 `Alice@example.com` 和 `alice@example.com` 注册成两个账号。
3. 查询数据库里是否已经存在该邮箱。存在时返回 409，而不是再次插入。
4. `hash_password()` 生成随机盐并计算 scrypt 哈希。
5. 数据库只保存 `hashed_password`，不保存原始密码。
6. `commit()` 提交事务，`refresh()` 从数据库重新加载自动生成的 `id` 和 `created_at`。

密码哈希不是加密。加密可以解密，密码哈希不能还原。项目保存的格式类似：

```text
scrypt$N$r$p$salt$digest
```

中间参数也一起保存，所以以后即使调整成本参数，旧密码仍然可以验证。

`verify_password()` 使用 `hmac.compare_digest()` 比较摘要，而不是直接使用 `==`。这样比较耗时不会因为前几位是否相同而出现明显差异，可降低时序攻击风险。

登录函数 `login` 做四件事：

1. 使用邮箱查询用户。
2. 找不到用户或密码不正确时，统一返回 401。
3. 用户被禁用时返回 403。
4. 验证成功后签发 JWT。

JWT 的核心载荷只有：

```json
{
  "sub": "1",
  "exp": 1780000000
}
```

`sub` 是用户 ID，`exp` 是过期时间。JWT 会被签名，但没有加密，因此不能把密码、手机号等敏感数据放进去。任何人都能读取载荷，只有持有服务端 `SECRET_KEY` 的一方能生成有效签名。

### 本节检查点

1. 为什么注册前要把邮箱转成小写？
2. 为什么数据库不能保存明文密码？
3. 为什么密码哈希要使用随机盐？
4. JWT 的 `sub` 和 `exp` 分别表示什么？

## 第 2 节：每个受保护接口如何识别当前用户

打开 `src/taskflow/api/dependencies.py`。

`get_current_user` 是鉴权入口：

1. `HTTPBearer(auto_error=False)` 读取 `Authorization` 请求头。
2. 请求头缺失或不是 Bearer 格式时返回 401。
3. `decode_access_token()` 校验签名和过期时间。
4. 从 `sub` 中取得用户 ID。
5. 按 ID 查询用户，并检查账号是否仍然有效。
6. 返回 `User` 对象，供路由函数使用。

路由里写：

```python
current_user: CurrentUser
```

FastAPI 就会先执行整条鉴权链。这样不需要在每个路由中重复复制 token 解析代码。

### 本节检查点

1. 没有 token 访问 `/api/v1/projects` 会得到什么状态码？
2. 依赖注入相比每个接口手写鉴权，减少哪类重复代码？
3. token 签名正确但用户已经被删除，会不会继续访问成功？

## 第 3 节：用户隔离，防止水平越权

水平越权是指普通用户 A 通过猜测资源 ID，读取或修改用户 B 的资源。TaskFlow 对项目使用 `OwnedProject` 依赖，对任务使用带 `join` 的所有权查询。

项目隔离代码：

```python
project = db.get(Project, project_id)
if project is None or project.owner_id != current_user.id:
    raise HTTPException(status_code=404, detail="Project not found")
```

任务的隔离不只是检查 `Task.project_id`，还要通过项目表确认当前用户是项目所有者：

```python
select(Task)
    .join(Project)
    .where(Task.id == task_id, Project.owner_id == current_user.id)
```

跨用户访问统一返回 404，而不是说明“资源存在但没权限”。这样不会向攻击者泄露某个 ID 是否真实存在。

保持服务运行，双击项目根目录的：

```text
verify_isolation.bat
```

脚本会自动注册 Alice 和 Bob，并依次验证：

- Bob 读取 Alice 的项目：404。
- Bob 修改 Alice 的项目：404。
- Bob 在 Alice 的项目下创建任务：404。
- Alice 读取自己的项目：200。

看到 `USER ISOLATION PASSED` 就表示隔离逻辑通过真实 HTTP 验证。

### 本节检查点

1. `OwnedProject` 为什么只保留一个项目参数，却能同时完成身份和权限检查？
2. 为什么跨用户访问返回 404，而不是 403？
3. 任务查询为什么需要关联 `Project` 表？

## 第 4 节：项目 CRUD、分页和筛选

打开 `src/taskflow/api/routes/projects.py`。

`create_project` 从 `current_user.id` 取得所有者，不接收客户端传来的 `owner_id`。客户端无法伪造“帮其他用户创建项目”。

`list_projects` 的查询分为三步：

1. 先构造固定过滤条件 `Project.owner_id == current_user.id`。
2. 有搜索词时，追加名称或描述模糊匹配。
3. 先执行 `COUNT` 得到总数，再使用 `offset` 和 `limit` 取当前页。

分页公式：

```text
offset = (page - 1) * page_size
```

例如第 3 页、每页 20 条，会跳过前 40 条，再取最多 20 条。

分页不是前端装饰，而是后端资源保护。如果一次返回十万条数据，数据库、网络和浏览器都会承受不必要压力。

`ProjectUpdate` 使用：

```python
payload.model_dump(exclude_unset=True)
```

只更新客户端明确提交的字段。没有提交的字段保持原值，因此 PATCH 不需要先读取并重发完整对象。

### 本节检查点

1. 为什么创建项目时不能让客户端直接提交 `owner_id`？
2. `page=3`、`page_size=20` 时 `offset` 是多少？
3. PATCH 和 PUT 在语义上有什么区别？

## 第 5 节：任务、级联删除和统计

打开 `src/taskflow/api/routes/tasks.py`、`src/taskflow/models/project.py` 和 `src/taskflow/models/task.py`。

任务列表始终以 `Task.project_id == project.id` 作为基础过滤条件。`project` 来自 `OwnedProject`，所以不存在先查出任务、再忘记校验所有者的路径。

任务状态和优先级使用 `StrEnum`，数据库保存的是 `todo`、`done`、`high` 等明确字符串。与直接保存整数相比，查看数据库时可读性更好；与不校验的普通字符串相比，拼错值会在进入业务逻辑前被拒绝。

级联删除分三层保证：

1. `Task.project_id` 设置 `ondelete="CASCADE"`，数据库知道项目删除后任务也应删除。
2. `Project.tasks` 设置 `cascade="all, delete-orphan"` 和 `passive_deletes=True`，SQLAlchemy 会话行为与数据库约束保持一致。
3. SQLite 默认不一定开启外键约束，因此 `database.py` 对每个连接执行 `PRAGMA foreign_keys=ON`。

项目统计接口一次 `GROUP BY status` 查询得到各状态数量，再单独统计逾期任务：

- 逾期条件是 `due_date < today`。
- 已完成和已取消任务不计为逾期。
- 完成率是 `done / total * 100`。
- `total == 0` 时完成率为 0，避免除零错误。

### 本节检查点

1. 如果 SQLite 没有开启外键约束，删除项目后可能出现什么问题？
2. “已完成但截止日期是昨天”的任务为什么不应算逾期？
3. 为什么完成率要在后端计算，而不是只让前端计算？

## 第 6 节：自动化测试和 CI

打开 `tests/conftest.py`。测试环境不会使用开发用的 `taskflow.db`，而是：

1. 在 pytest 临时目录创建独立的 `test.db`。
2. 创建测试专用 Engine 和 Session。
3. 在 FastAPI 中用 `dependency_overrides` 替换正式 `get_db`。
4. 每个测试结束后删除表并释放连接。

这样测试不会污染本地数据，也不会因为测试顺序不同而互相影响。

运行全部检查：

```text
run_tests.bat
```

等价命令：

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest --cov=taskflow --cov-report=term-missing
```

12 项测试覆盖：

- 健康检查和 `/demo` 页面。
- 注册、登录、当前用户。
- 重复注册、错误密码、缺失 token、短密码。
- 项目 CRUD、搜索、跨用户隔离。
- 任务 CRUD、筛选、统计、跨用户隔离和级联删除。

GitHub Actions 在每次推送后自动执行相同检查。CI 的价值不是“多一个徽章”，而是证明项目在干净环境中也能安装依赖并通过测试。

### 本节检查点

1. 测试为什么使用临时数据库？
2. `dependency_overrides` 解决了什么问题？
3. CI 文件和本地测试命令相比，多验证了什么？

## 90 秒面试介绍稿

> TaskFlow API 是我用 Python 做的一个多用户项目与任务管理后端，技术栈是 FastAPI、SQLAlchemy 2.0、Pydantic 2 和 JWT。它支持用户注册登录、项目和任务 CRUD、分页搜索、状态与优先级筛选，以及项目维度的完成率和逾期统计。
>
> 项目里我最关注的不是接口数量，而是权限边界和可验证性。所有项目查询都绑定当前用户；任务查询会关联项目表检查所有者，因此用户猜到其他用户的 ID 也只能得到 404。JWT 只保存用户 ID 和过期时间，密码使用带随机盐的 scrypt 哈希。为避免每个接口重复鉴权，我把当前用户和资源所有权封装成 FastAPI 依赖。
>
> 项目还有 12 个 pytest 接口测试，覆盖重复注册、错误凭证、跨用户访问、筛选统计和级联删除，当前覆盖率约 94%。代码通过 Ruff 检查并由 GitHub Actions 在 Python 3.13 环境自动运行。项目本地使用 SQLite 零配置启动，也提供 PostgreSQL 和 Docker Compose 配置。后续我计划补充 Alembic 迁移、refresh token 和项目成员角色。

练习时先用 90 秒完整说一遍，再压缩成 60 秒。不要照抄背诵，应该把每一句都对应到实际代码。

## 高频追问与参考回答

### 为什么选 FastAPI？

FastAPI 与 Pydantic 的类型校验结合紧密，能自动生成 OpenAPI 文档，依赖注入适合统一处理鉴权和资源权限。它既减少样板代码，也没有隐藏路由和数据库层，适合展示完整后端思路。

### 为什么使用 SQLAlchemy 2.0？

SQLAlchemy 提供明确的对象关系映射和查询组合能力。项目使用 `select()`、`join()`、`group_by()` 等显式查询，可以同时支持 SQLite 和 PostgreSQL，而不是把 SQL 写死在某一个数据库上。

### JWT 有什么不足？

JWT 便于无状态水平扩展，但普通 access token 在过期前很难主动吊销。当前项目没有 refresh token、登出黑名单和权限版本号。生产系统应根据风险加入短有效期、刷新机制和令牌吊销策略。

### 为什么密码不用简单 SHA-256？

SHA-256 设计目标是快速计算，GPU 可以极高速枚举。scrypt 有意消耗更多内存和 CPU，并增加每个密码的随机盐，使离线暴力破解成本更高。

### 如果任务量达到百万级，统计接口怎么优化？

先根据真实慢查询确认瓶颈。常用筛选字段可以建立组合索引；高频统计可使用缓存，但必须定义项目更新后的失效策略；更大规模可以异步汇总到统计表，而不是每次实时全量聚合。

## 学完后的下一轮开发顺序

1. 给任务增加标签，并实现多标签筛选。
2. 增加项目成员和 `owner`、`member`、`viewer` 角色。
3. 增加 Alembic 数据库迁移。
4. 增加 refresh token、登出和令牌黑名单。
5. 使用 Redis 缓存统计，并处理缓存一致性。
6. 部署到云平台，配置 HTTPS、日志和监控。

每完成一项，都同步增加测试、README 说明和面试问答。没有实际完成的功能不要写进简历。
