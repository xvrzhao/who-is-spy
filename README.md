# 谁是卧底

和一桌 Agent 一起玩 “谁是卧底” ！

## 特色功能

- 每个 Agent 都有自己独立的记忆，包括游戏中各玩家的发言投票、自己的心理推测独白等。
- 每个 Agent 都是真实语音发言，发言内容和投票决策使用语言模型，语音播放采用 MiniMax 的语音模型，每个 Agent 都有自己独特的音色、语气，具有人的温度。
- 每个 Agent 发言前都会有私密推理（我是卧底吗、谁可疑），卧底会主动伪装，Agent 的发言也会站队、拉拢、排挤等，真实感很强。
- 精彩的是游戏结束后，大家会有交流复盘环节，你和 Agent 之间一起对话，说说谁是“奥斯卡”、谁很冤、评评理、夸夸人，话题是开放的。

## 架构

项目采用前后端架构，前后端之间采用传统 HTTP 通信，前端请求推动后端 Langgraph 节点执行，后端通过 SSE 返回游戏进度事件。

游戏核心逻辑，也就是 Langgraph 图，在 `backend/src/core/game/` 中。后端纯手写，前端 Vibe Coding 生成。

```mermaid
flowchart LR
    fe["前端 · Vue<br/>游戏 UI"]
    be["后端 · FastAPI + LangGraph<br/>游戏状态图"]
    fe -- "POST /api/games<br>（开局）" --> be
    fe -- "POST /api/games/{thread_id}/resume<br>（应答 interrupt）" --> be
    be -- "SSE 事件流" --> fe
    be --> llm["智谱 GLM<br/>推理 · 发言 · 投票"]
    be --> tts["MiniMax TTS"]
    be --> pg[("Postgres<br/>checkpoint")]
```

后端把整局游戏编排成一张 LangGraph 状态图：AI 节点调 LLM/TTS 产出发言，轮到真人时图在 `interrupt` 处挂起，前端提交输入后 `resume` 续跑，每一步状态都 checkpoint 进 Postgres。前端是纯展示/交互层，解析 SSE 事件流驱动 UI、管理语音播放队列、收集真人的发言和投票。

真人和后端的交互只有两个接口：开局、应答 interrupt。每应答一次，后端返回一段新的 SSE 流。

部署到云端就是三个容器：

```mermaid
flowchart LR
    b["浏览器"] --> web["web（nginx）<br/>静态资源 + 反代 /api · 对外 WEB_PORT"] --> app["app（FastAPI）<br/>仅容器内网"] --> db[("postgres<br/>仅绑 127.0.0.1")]
```

## 技术栈

- 前端：Vue 3 / Vite / TypeScript / Pinia
- 后端：Python 3.14 / FastAPI / LangGraph，LLM 走智谱 GLM（OpenAI 兼容协议），TTS 用 MiniMax
- 存储：Postgres（langgraph checkpoint）
- 部署：Docker Compose

## 本地开发

依赖：Python 3.14+、Node 20+、Docker。

```bash
# 1. 配置
cp backend/.env.example backend/.env
#    填 LLM_API_KEY（智谱，必填）、MINIMAX_API_KEY（可选，不填就没有语音）

# 2. 起 Postgres
docker compose up -d postgres

# 3. 起后端（:8000）
cd backend
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --port 8000

# 4. 起前端（:5173，/api 由 vite proxy 转到 8000）
cd frontend
npm install && npm run dev
```

打开 http://localhost:5173 开局。懒得配后端的话，mock 模式可以直接玩：`cd frontend && VITE_USE_MOCK=1 npm run dev`。

## 云端部署

```bash
docker compose --env-file backend/.env up -d --build
```

`.env` 随代码迁到了 `backend/` 下，compose 插值要用的 `PG_*` / `WEB_PORT` 得靠 `--env-file backend/.env` 指过去；也可以在部署机 `export COMPOSE_ENV_FILES=backend/.env`，之后不用每次带。注意不带 `--env-file` 不会报错，只是插值静默用默认值。

三个服务的分工：

- web：nginx 托管前端构建产物并反代 `/api` 到 app，同源没有 CORS 问题，对外端口 `WEB_PORT`（默认 80）
- app：后端，只在容器内网可达，密钥经 `env_file` 运行时注入，不进镜像
- postgres：数据落 named volume，端口只绑 127.0.0.1，要调试可以走 SSH 隧道连

## 目录

```
backend/             FastAPI + LangGraph 后端（目录结构 / graph 流程见 backend/README.md）
frontend/            Vue3 前端（运行说明 / mock 开关见 frontend/README.md）
docker-compose.yml   云端整套部署编排
```

配置全部集中在 `backend/.env`，逐项说明见 [backend/README.md](backend/README.md#配置env)。
