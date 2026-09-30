# 谁是卧底

和一桌 AI 玩「谁是卧底」：你是唯一的真人玩家，其余由 LLM Agent 扮演。轮流发言描述自己的词、投票淘汰嫌疑人——揪出卧底则平民胜，卧底存活到最后则卧底胜。终局后还有一轮全员赛后交流，听听 AI 们怎么复盘这局。

## 功能特性

- **完整对局规则**：轮流发言 → 全员投票（支持弃票、平票加赛）→ 淘汰，直到分出胜负
- **有内心戏的 AI 玩家**：每个 Agent 先私密推理（我是不是卧底？谁可疑？），再组织当众发言；卧底会主动伪装
- **语音对局**：AI 发言经 TTS 合成（每名玩家固定音色），前端自动连播，节奏接近真实牌局
- **实时体验**：发言、投票、淘汰、揭晓全部通过 SSE 实时推送上屏
- **拟真圆桌 UI**：座位 + 麦克风 + 聊天时间线 + 阶段提示，你的词常驻底部词牌
- **mock 模式**：前端内置剧本驱动整局流程，无需后端与 API Key 即可体验

## 总体架构

```
┌─────────────────┐   POST /api/*（HTTP + SSE 流）   ┌──────────────────┐
│     frontend     │ ──────────────────────────────▶ │     backend      │
│  Vue3 + Vite     │                                 │  FastAPI +       │
│  拟真圆桌 / 语音  │ ◀────────────────────────────── │  LangGraph 状态机 │
│  连播 / 状态机    │        游戏事件（SSE 帧）         │        │         │
└─────────────────┘                                 └────────┼─────────┘
                              ┌───────────────┬───────────────┼─────────┐
                              ▼               ▼               ▼         
                        智谱 GLM（LLM）   MiniMax（TTS）   Postgres（checkpoint）
```

- **后端**用 LangGraph 把整局游戏编排成一张状态图：AI 节点调 LLM/TTS 产出发言，轮到真人时图在 `interrupt` 上挂起，前端提交输入后 `resume` 续跑；每步状态 checkpoint 进 Postgres
- **前端**是纯展示/交互层：解析 SSE 事件流驱动 UI，管理语音播放队列，收集真人发言/投票
- 真人与后端的所有交互只有两个接口：**开局**与**应答 interrupt**，每应答一次返回一段新的 SSE 事件流

**云端部署形态**（docker compose 三容器）：

```
浏览器 ──▶ web（nginx：托管前端静态资源 + 反代 /api） ──▶ app（FastAPI，仅内网） ──▶ postgres（仅绑 127.0.0.1）
```

## 技术栈

| | |
|---|---|
| 前端 | Vue 3 · Vite · TypeScript · Pinia |
| 后端 | Python 3.14 · FastAPI · LangGraph · langchain-openai（智谱 GLM）· MiniMax TTS |
| 存储 | Postgres（langgraph checkpoint） |
| 部署 | Docker Compose（postgres + app + web/nginx） |

## 快速开始（本地开发）

依赖：Python 3.14+、Node 20+、Docker。

```bash
# 1. 配置：从模板生成 .env，填入你的 Key
cp backend/.env.example backend/.env
#    LLM_API_KEY     智谱开放平台 Key（必填）
#    MINIMAX_API_KEY MiniMax Key（可选，缺省则对局无语音）

# 2. 起依赖（Postgres）
docker compose up -d postgres

# 3. 起后端（:8000）
cd backend
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --port 8000

# 4. 起前端（:5173，/api 经 vite proxy 转发到 8000）
cd frontend
npm install && npm run dev
```

打开 http://localhost:5173 开局。**不想配后端？** mock 模式一键体验：`cd frontend && VITE_USE_MOCK=1 npm run dev`。

## 云端部署（Docker Compose）

```bash
docker compose --env-file backend/.env up -d --build
```

- `--env-file backend/.env`：配置已随代码迁入 `backend/`，插值变量（`PG_*` / `WEB_PORT`）从那里读取；也可在部署机 `export COMPOSE_ENV_FILES=backend/.env` 一劳永逸
- `web`：nginx 托管前端构建产物并反代 `/api` → `app`（同源，无 CORS 问题），对外端口 `WEB_PORT`（默认 80）
- `app`：后端，仅容器内网可达，密钥经 `env_file` 运行时注入（不进镜像）
- `postgres`：数据落 named volume，端口只绑回环地址（可走 SSH 隧道调试）

## 目录

```
├── backend/            # FastAPI + LangGraph 游戏后端（目录结构 / graph 流程详见 backend/README.md）
├── frontend/           # Vue3 前端（运行说明 / mock 调试开关详见 frontend/README.md）
├── docker-compose.yml  # 云端整套部署编排
└── README.md
```

## 配置项

全部配置集中在 `backend/.env`（模板见 `backend/.env.example`）：LLM / TTS Key、Postgres 连接、部署环境与端口等，逐项说明见 [backend/README.md](backend/README.md#配置env)。
