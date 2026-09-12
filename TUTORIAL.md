# TaskFlow API 保姆级教程

这份教程面向 Python 基础一般、第一次做完整后端项目的学习者。按顺序做，不要一开始就试图读懂所有代码。

完成后的目标：

- 能在浏览器中注册、登录、创建项目和任务。
- 能说出一次请求从路由到数据库的完整过程。
- 能运行 12 个自动化测试。
- 能使用 Docker 启动 PostgreSQL 版本。
- 能把这个项目用 60 秒讲给面试官。

预计时间：每天 1 到 2 小时，连续 7 天。第一天先跑通，不要求全部理解。

## 第 1 天：启动项目

### 一键启动

如果你不熟悉 PowerShell，直接双击项目根目录中的：

```text
start_taskflow.bat
```

脚本会自动完成以下工作：

1. 检查并创建 `.venv` 虚拟环境。
2. 检查并安装缺失依赖。
3. 从 `.env.example` 生成包含随机密钥的 `.env`。
4. 如果 8000 端口被占用，自动选择 8001 到 8100 之间的空闲端口。
5. 启动 FastAPI 并打开 `/demo` 浏览器操作台。

脚本窗口不要关闭，它需要保持运行。关闭窗口或按 `Ctrl+C` 就会停止服务。

需要停止服务时，也可以双击：

```text
stop_taskflow.bat
```

只有一键启动失败时，才需要继续执行下面的手工步骤，并把脚本窗口中的完整报错发给我。

### 1. 检查 Python

打开 PowerShell，执行：

```powershell
python --version
```

需要 Python 3.11 或更高版本。本项目已经在 Python 3.14 下验证通过。

### 2. 进入项目

```powershell
cd "C:\path\to\taskflow-api"
```

把示例路径替换成你电脑上的实际项目目录，然后查看目录：

```powershell
Get-ChildItem
```

你应该看到 `src`、`tests`、`pyproject.toml`、`TUTORIAL.md` 等文件。

### 3. 创建虚拟环境

虚拟环境的作用是把当前项目的依赖与电脑里的其他 Python 项目隔离开。

```powershell
python -m venv .venv
```

激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 提示禁止运行脚本，可以不激活，后续统一使用 `.\.venv\Scripts\python.exe`。这是更稳妥的 Windows 用法。

### 4. 安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`-e` 表示可编辑安装。修改 `src` 下的代码后无需重新安装。

安装成功时，最后一行通常包含：

```text
Successfully installed fastapi ... sqlalchemy ... taskflow-api ...
```

### 5. 创建配置文件

```powershell
Copy-Item .env.example .env
```

打开 `.env`，至少修改 `SECRET_KEY`：

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

把输出粘贴到：

```dotenv
SECRET_KEY=这里粘贴随机字符串
```

不要把真实 `.env` 提交到 GitHub。`.gitignore` 已经忽略它。

### 6. 启动服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn taskflow.main:app --reload
```

看到下面的信息表示成功：

```text
Uvicorn running on http://127.0.0.1:8000
```

浏览器打开：

```text
http://127.0.0.1:8000/demo
```

操作台就是本项目最简单的可视化管理界面。页面预填了本地演示账号，登录后可以创建项目、创建任务、标记完成和查看统计。Swagger 仍然保留在 `http://127.0.0.1:8000/docs`，后面用于查看接口定义，不再承担新手授权练习。

### 第 1 天检查点

- `http://127.0.0.1:8000/health` 返回 `{"status":"ok","environment":"development"}`。
- 操作台页面能正常显示。
- 停止服务时在终端按 `Ctrl+C`。

## 第 2 天：在操作台中走通业务

打开 `http://127.0.0.1:8000/demo`。页面已经预填测试账号：

```text
邮箱：demo@example.com
密码：12345678
```

这个账号只用于本地学习和验收，不要在生产环境继续使用默认密码。

### 1. 登录并确认身份

点击“登录”。页面右上角变成“已登录”，下方响应区域显示登录请求返回的 `200` 状态。再点击“读取当前用户”，响应中应该包含：

```json
{"id": 1, "email": "demo@example.com", "full_name": "Alice"}
```

这一步证明登录成功后拿到的 JWT 能通过受保护接口。操作系统隐藏了 token 的复制和请求头拼接过程，但实际发出的请求仍然使用 `Authorization: Bearer <access_token>`。

### 2. 创建项目

在“创建项目”区域填写项目名称和说明，然后点击“创建项目”。例如：

```json
{
  "name": "我的第一个项目",
  "description": "通过 TaskFlow 操作台创建"
}
```

创建成功后，项目列表会自动刷新并选中新项目。响应区域会显示请求的 `POST` 路径和 `201` 状态，其中的 `id` 就是项目编号。

### 3. 创建任务

确认“项目列表”中选中了刚才创建的项目。在“任务操作”区域填写任务标题并选择优先级，然后点击“创建任务”。例如：

```json
{
  "title": "完成第一次 API 测试",
  "priority": "medium"
}
```

创建成功后，任务列表会刷新。选择该任务，列表文本末尾应显示 `[todo]`。

### 4. 完成任务

在“选择任务”下拉框中选择刚才创建的任务，点击“标记完成”。任务列表刷新后，选中项的末尾应变成 `[done]`。

### 5. 查看统计

保持项目选中，点击“查看统计”。响应中至少应包含：

```json
{
  "total": 1,
  "todo": 0,
  "in_progress": 0,
  "done": 1,
  "cancelled": 0,
  "overdue": 0,
  "completion_rate": 100.0
}
```

这些结果来自数据库实时聚合，不是前端写死的数字。

### 第 2 天检查点

你能在不用查教程的情况下完成：

```text
登录 -> 读取当前用户 -> 创建项目 -> 创建任务 -> 标记完成 -> 查看统计
```

完成后，再打开 `http://127.0.0.1:8000/docs` 找到刚才调用过的接口。你不需要在 Swagger 中重新授权，只要能把界面上的按钮和对应的 HTTP 方法、路径对应起来即可。

## 第 3 天：理解目录和请求流程

核心目录：

```text
src/taskflow/
├─ api/
│  ├─ dependencies.py
│  └─ routes/
│     ├─ auth.py
│     ├─ projects.py
│     └─ tasks.py
├─ models/
├─ schemas/
├─ config.py
├─ database.py
├─ security.py
└─ main.py
```

每层只做一件事：

| 层 | 作用 | 例子 |
| --- | --- | --- |
| Route | 接收 HTTP 请求 | `create_project` |
| Dependency | 验证身份和权限 | `get_current_user` |
| Schema | 校验输入和定义输出 | `ProjectCreate` |
| Model | 描述数据库表 | `Project` |
| Database | 创建连接和事务 | `SessionLocal` |
| Security | 密码和 JWT | `hash_password` |

一次“创建任务”请求的流程：

1. FastAPI 把 JSON 转成 `TaskCreate`。
2. `OwnedProject` 依赖检查项目是否存在且属于当前用户。
3. 路由创建 `Task` 模型并加入数据库会话。
4. `db.commit()` 写入数据库。
5. SQLAlchemy 返回任务 ID 和创建时间。
6. FastAPI 用 `TaskRead` 把模型转换成 JSON。

### 阅读顺序

不要从 `main.py` 开始逐行读。建议按下面顺序：

1. `schemas/task.py`
2. `models/task.py`
3. `api/routes/tasks.py`
4. `api/dependencies.py`
5. `database.py`

第一次阅读只需要知道数据从哪里来、去了哪里，不需要记住所有语法。

### 第 3 天练习

1. 打开 `models/task.py`，找出四种任务状态。
2. 打开 `schemas/task.py`，找出创建任务时的必填字段。
3. 打开 `api/routes/tasks.py`，找出筛选状态和优先级的代码。
4. 给出“查询一个不属于自己的任务”时使用的 SQL 条件。

## 第 4 天：理解鉴权和用户隔离

注册时：

1. 邮箱统一转小写。
2. 检查邮箱是否已存在。
3. 使用随机 salt 和 scrypt 计算密码哈希。
4. 数据库只保存哈希，不保存明文密码。

登录时：

1. 根据邮箱找到用户。
2. 用 `verify_password` 重新计算哈希并安全比较。
3. 验证成功后创建 JWT。

JWT 里的核心内容：

```json
{
  "sub": "1",
  "exp": 1780000000
}
```

`sub` 是用户 ID，`exp` 是过期时间，不包含密码。

用户隔离的关键代码在 `api/dependencies.py`：

```python
project = db.get(Project, project_id)
if project is None or project.owner_id != current_user.id:
    raise HTTPException(status_code=404, detail="Project not found")
```

查询任务时也通过 `join(Project)` 检查 `owner_id`。因此 A 用户即使猜到 B 用户的任务 ID，也得不到数据。

### 第 4 天练习

1. 把 token 过期时间改成 5 分钟，重新登录并观察。
2. 使用错误密码登录，确认返回 401。
3. 注册两个用户，用 Bob 的 token 访问 Alice 的项目，确认返回 404。
4. 用自己的话解释为什么密码哈希必须有随机 salt。

## 第 5 天：运行测试并故意制造一次失败

执行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

预期：

```text
12 passed
```

查看覆盖率：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=taskflow --cov-report=term-missing
```

代码检查：

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

现在修改 `tests/test_auth.py`，把重复注册的预期状态码从 `409` 改成 `200`，再次运行测试。你会看到测试失败。把代码改回 `409` 后再次运行。

这一步的目的不是学测试语法，而是确认你真的理解“测试失败时如何定位问题”。

### 第 5 天练习

在 `tests/test_tasks.py` 中新增一个测试：

1. 创建两个任务。
2. 删除其中一个。
3. 查询项目统计。
4. 断言总任务数变为 1。

## 第 6 天：Docker 和 PostgreSQL

安装 Docker Desktop 后，在项目目录执行：

```powershell
docker compose up --build
```

Docker Compose 会启动：

- `api`: FastAPI 服务，端口 8000。
- `db`: PostgreSQL 17，数据保存在 Docker volume。

打开：

```text
http://127.0.0.1:8000/docs
```

停止服务：

```powershell
docker compose down
```

如果还要删除数据库数据：

```powershell
docker compose down -v
```

`down -v` 会永久删除数据库 volume，只在你确定不需要数据时执行。

### 第 6 天练习

1. 在 PostgreSQL 环境中注册一个用户并创建任务。
2. 执行 `docker compose restart`，确认数据仍然存在。
3. 解释 SQLite 和 PostgreSQL 两种环境的区别。

## 第 7 天：发布到 GitHub

在项目目录初始化 Git：

```powershell
git init
git add .
git commit -m "feat: build taskflow api"
```

创建一个空 GitHub 仓库，不要勾选自动生成 README。然后：

```powershell
git remote add origin https://github.com/你的用户名/taskflow-api.git
git branch -M main
git push -u origin main
```

推送后打开 GitHub 的 `Actions` 页面，确认 CI 中的 Ruff 和 pytest 都通过。

### 第 7 天检查点

- GitHub 上能看到 `README.md`、`TUTORIAL.md`、测试和工作流。
- 没有提交 `.venv`、`.env` 或 `taskflow.db`。
- CI 显示绿色。
- 你能用 60 秒讲清项目背景、技术方案、难点和结果。

## 常见问题

### `Activate.ps1` 无法加载

不激活即可，所有命令都改为：

```powershell
.\.venv\Scripts\python.exe -m ...
```

### 8000 端口被占用

换一个端口：

```powershell
.\.venv\Scripts\python.exe -m uvicorn taskflow.main:app --reload --port 8001
```

操作台地址改为 `http://127.0.0.1:8001/demo`，Swagger 地址改为 `http://127.0.0.1:8001/docs`。

### 修改 `.env` 后没有生效

停止服务并重新启动。修改代码时 Uvicorn 会自动重载，修改 `.env` 时不一定自动重新读取。

### 数据库结构改了但程序报错

当前项目适合本地快速开发，启动时会自动建表。自动建表不会修改已有表的字段。学习阶段可以删除 `taskflow.db` 后重启；真实生产项目应使用 Alembic 迁移。

### 测试时提示端口占用

本项目测试使用 FastAPI `TestClient`，不会占用 8000 端口。如果出现端口错误，通常是代码中误用了真实 HTTP 服务。

## 完成之后怎么继续提升

按 `docs/RESUME_GUIDE.md` 的顺序做增强，一次只加一个功能：

1. 任务标签与多标签筛选。
2. 项目成员和角色权限。
3. Refresh token 与登出。
4. Alembic 数据库迁移。
5. Redis 统计缓存。
6. 云服务器部署、HTTPS 和监控。

每加一个功能，都补测试、更新 README，并能解释技术选择。这样它才会真正成为你的项目，而不只是仓库里的代码。
