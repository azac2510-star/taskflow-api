# TaskFlow API

TaskFlow 是一个可直接写进简历的多用户项目与任务管理后端。它不只是一个 CRUD 示例，还包含 JWT 鉴权、用户数据隔离、分页筛选、统计接口、自动化测试、Docker 和 CI。

## 项目亮点

- 使用 FastAPI + SQLAlchemy 2.0 构建分层清晰的 REST API
- 使用 JWT 实现注册、登录和当前用户鉴权
- 所有项目和任务都按用户隔离，防止水平越权
- 支持项目/任务 CRUD、搜索、分页、状态与优先级筛选
- 统计接口提供完成率、进行中数量和逾期任务数
- 内置 `/demo` 浏览器操作台，新手无需配置 Swagger 授权即可走通业务
- 12 个 pytest 测试覆盖鉴权、隔离、筛选和级联删除
- 提供一键用户隔离验证脚本，用真实 HTTP 检查跨用户越权场景
- Docker Compose 一键启动 API + PostgreSQL
- GitHub Actions 自动执行 Ruff 和 pytest

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0 |
| 数据校验 | Pydantic 2 |
| 数据库 | SQLite（本地）/ PostgreSQL（Docker） |
| 鉴权 | OAuth2 Password Flow + JWT |
| 密码存储 | `hashlib.scrypt` 加盐哈希 |
| 测试 | pytest + FastAPI TestClient |
| 代码质量 | Ruff + GitHub Actions |
| 部署 | Docker Compose |

## 架构

```text
HTTP Request
    |
FastAPI Router
    |
CurrentUser / OwnedProject dependency
    |
SQLAlchemy Session
    |
SQLite or PostgreSQL
```

依赖注入把“当前用户”和“当前用户拥有的项目”统一放到路由入口。业务代码无需重复查询权限，跨用户访问统一返回 404，避免泄露资源是否存在。

## 目录结构

```text
taskflow-api/
├─ src/taskflow/
│  ├─ api/
│  │  ├─ dependencies.py
│  │  └─ routes/
│  ├─ models/
│  ├─ schemas/
│  ├─ config.py
│  ├─ database.py
│  ├─ main.py
│  └─ security.py
├─ tests/
├─ .github/workflows/ci.yml
├─ compose.yaml
├─ Dockerfile
├─ pyproject.toml
└─ TUTORIAL.md
```

## 本地启动

最简单的启动方式是双击项目根目录中的 `start_taskflow.bat`。脚本会自动检查虚拟环境和依赖，创建 `.env`，选择空闲端口，启动 API 并打开 `/demo` 浏览器操作台。

需要停止服务时，双击项目根目录中的 `stop_taskflow.bat`。

如果双击脚本无法启动，再使用下面的手动命令。

Windows PowerShell：

```powershell
cd "C:\path\to\taskflow-api"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn taskflow.main:app --reload
```

把示例路径替换成你电脑上的实际项目目录。

打开：

- 浏览器操作台: http://127.0.0.1:8000/demo
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Health check: http://127.0.0.1:8000/health

操作台内置了本地演示账号的登录入口，登录后可以依次完成创建项目、创建任务、标记完成和查看统计。Swagger 仍保留给需要查看接口定义或调试请求的开发者。

默认使用 `taskflow.db`，不需要安装数据库。

## 测试与质量检查

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=taskflow --cov-report=term-missing
```

服务启动后，还可以执行真实 HTTP 冒烟测试：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

再执行用户隔离验证：

```powershell
.\.venv\Scripts\python.exe scripts\verify_isolation.py
```

也可以直接双击 `verify_isolation.bat`。脚本会创建两个临时用户，验证跨用户读取、修改项目和创建任务全部返回 404。

## Docker 启动

```bash
docker compose up --build
```

这会启动 PostgreSQL 和 API。生产环境应改用随机密钥、数据库迁移和受控的 `AUTO_CREATE_TABLES=false`。

## 主要接口

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录并获取 JWT |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET/POST | `/api/v1/projects` | 项目分页列表/创建项目 |
| GET/PATCH/DELETE | `/api/v1/projects/{id}` | 项目详情/修改/删除 |
| GET | `/api/v1/projects/{id}/stats` | 项目任务统计 |
| GET/POST | `/api/v1/projects/{id}/tasks` | 任务列表/创建任务 |
| GET/PATCH/DELETE | `/api/v1/tasks/{id}` | 任务详情/修改/删除 |

完整学习步骤见 [TUTORIAL.md](TUTORIAL.md)，代码与面试讲解见 [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md)，简历写法见 [docs/RESUME_GUIDE.md](docs/RESUME_GUIDE.md)。可打印的完整 Word 手册见 [docs/TaskFlow_API_Project_Guide_ZH_v4.docx](docs/TaskFlow_API_Project_Guide_ZH_v4.docx)。

## 简历描述模板

> TaskFlow API：基于 FastAPI、SQLAlchemy 和 JWT 的多用户任务管理后端。设计 OAuth2 登录与资源所有权校验，实现项目/任务 CRUD、分页筛选和完成率统计；提供浏览器操作台便于验收核心流程，使用 SQLite/PostgreSQL 双环境、Docker Compose 和 GitHub Actions 完成开发、测试与部署流程，自动化测试覆盖 12 个核心场景。
