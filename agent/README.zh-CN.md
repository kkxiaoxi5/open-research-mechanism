# mechanism-agent —— 机制的可运行代码

**简体中文** | [English](README.md) | [日本語](README.ja.md)

本仓库的文档描述了一套让多代理研究不漂移、不停摆、不自欺的机制。
这个文件夹是同一套机制的一个小型、零依赖的参考实现
（Python ≥ 3.11，仅标准库），单机——包括内网机器——即可端到端运行。

## 里面有什么

| 模块 | 它实现的机制部件 |
|---|---|
| `board.py` | 追加式认领板（JSONL + 文件锁）。叶子关单只有 **证成 / 证否 / 拆小** 三态——「判不出」在写入时直接拒绝。卡住必须留说明，并派生一张换角度的子叶。 |
| `agents.py` | 工作代理（提出答案）与复核代理（用事先登记的已知答案检查器独立复算）。作者永远关不了自己的叶——代码强制，不是约定。 |
| `orchestrator.py` | 一轮叫醒：对账过期租约与卡住叶 → 派发 → 复核 → 导出快照。 |
| `backend.py` | 可插拔模型后端：确定性假后端（无 key 跑通演示）与 OpenAI 兼容客户端（接公网或内网模型）。 |
| `tracker.py` | 人类规模票据（任务 / 质问 / 决定，带「等决定」队列）与**快照导出**——票据状态永不只活在一个服务里。 |
| `webapp.py` | 互动控制台：左侧任务栏（等你定、认领板、票据、成员管理、关系图），中间是按成员分频道的持久聊天栏，右侧 Prompt 导航可从任意一条消息分叉会话。成员可在「成员」页增删并单独设模型参数（模型、Base URL、temperature；key 只存环境变量名），协调者每轮按注册表重建工作队。所有写入都经与代理同一套 Board/Tickets 规则。 |
| `registry.py` / `chat.py` | 成员注册表（`agents.json`）与可分叉的只追加会话日志（`chat.jsonl`，消息带 parent 指针）。 |
| `skills/` + `skills.py` | 七个捆绑 playbook（拆叶、已知答案测试、反例猎杀、证明复核、形式化、证据记账、票据工作流），按角色装入各代理的提示词——工作习惯和机器一起发货。用 `skills` 命令可列出。 |

## 跑演示（无 key，一分钟）

```bash
cd agent
PYTHONPATH=src python -m mechanism_agent --home ./mech-state init
PYTHONPATH=src python -m mechanism_agent --home ./mech-state seed-demo
PYTHONPATH=src python -m mechanism_agent --home ./mech-state run
PYTHONPATH=src python -m mechanism_agent --home ./mech-state serve   # http://127.0.0.1:8765

一键部署：

```bash
git clone https://github.com/kkxiaoxi5/open-research-mechanism.git
cd open-research-mechanism/agent
./deploy.sh            # Linux/macOS：初始化 + 种子数据 + 启动控制台
.\deploy.ps1           # Windows PowerShell
docker compose up -d   # 服务器部署（状态存 volume）
```
```

演示种下三片叶子，一轮跑完三种结局：一个答案正确（**证成**），
一个答错、被复核代理复算抓住（**证否**），一个按原题答不出
（**拆小**成两片可判的子叶，随后证成关单）。

测试：`PYTHONPATH=src python -m unittest discover -s tests -v`

## 接真实模型

把 `MECH_AGENT_BASE_URL`、`MECH_AGENT_API_KEY`、`MECH_AGENT_MODEL`
指向任意 OpenAI 兼容接口（内网模型服务器即可），`run` 即改用它，
其余部件——认领板、票据、快照、看板——全部不变：
**内容与密钥留在你自己的机器上，被分享的只有机制。**

## 路线图

[PLAN.md](PLAN.md) 是 v0.2–v0.5 的计划书：Swarm 式协作（命名成员、
带提及的共享留言板、睡眠唤醒、监视员、跨模型复核）、Claude Code 式
对话界面与任务分支、Docker 服务端部署——每期都预先写明验收标准。

## v0.1 的范围

刻意做小：单机、无分布式、无权限系统（部署在你内网自身的
访问控制之后）。不做小的只有要紧的部分：关单规则、
作者/复核分离、快照契约，都是框架文档里的真规则，由代码强制执行。
