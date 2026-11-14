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
| `dashboard.py` | 只读可视化看板：等决定队列在第一屏，其后是认领板、票据、已关叶子的证据汇总。它没有任何写入口。 |

## 跑演示（无 key，一分钟）

```bash
cd agent
PYTHONPATH=src python -m mechanism_agent --home ./mech-state init
PYTHONPATH=src python -m mechanism_agent --home ./mech-state seed-demo
PYTHONPATH=src python -m mechanism_agent --home ./mech-state run
PYTHONPATH=src python -m mechanism_agent --home ./mech-state serve   # http://127.0.0.1:8765
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

## v0.1 的范围

刻意做小：单机、无分布式、无权限系统（部署在你内网自身的
访问控制之后）。不做小的只有要紧的部分：关单规则、
作者/复核分离、快照契约，都是框架文档里的真规则，由代码强制执行。
