# 智能健身教练系统（桌面版）

本目录是 **桌面版** 项目，面向论文/验收的桌面端形态：**Electron + Vue3 + FastAPI + SQLite + 进程内缓存**。

## 环境要求

- Node.js（建议 18+）
- Python 3.9+（建议与本机一致）

## 一键启动（推荐）

双击运行：

- `start_desktop.bat`

脚本会自动完成：

- 创建后端虚拟环境 `backend/.venv`
- 安装后端依赖
- 若 `frontend/dist` 不存在则构建前端
- 启动 MCP 网关（9001）
- 启动 Electron（Electron 会自动拉起后端 FastAPI，并自动选择可用端口）

## 手动启动（便于调试）

### 1) 后端（FastAPI）

进入 `backend/` 后运行：

```bash
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2) MCP 网关

```bash
.\.venv\Scripts\python -m uvicorn app.mcp.server:app --host 127.0.0.1 --port 9001
```

### 3) 前端构建

```bash
cd frontend
npm install
npm run build
```

### 4) Electron

```bash
cd electron
npm install
npm run start
```

## 配置说明（桌面版固定）

桌面版后端配置在 `backend/.env`，核心是：

- SQLite：`USERS_DATABASE_URL=sqlite:///...`、`SPORTS_DATABASE_URL=sqlite:///...`
- 进程内缓存：`REDIS_URL=memory://local`

首次启动会自动创建表并写入基础数据（管理员 `admin/123456`）。

