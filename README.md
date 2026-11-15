# Open Research Mechanism（开源研究机制框架）

**简体中文** | [English](README.en.md) | [日本語](README.ja.md)

> 一套让多个 AI 代理**协作创造新知识**的运转机制。
> 本仓库只发布**机制**：角色怎么分、任务怎么流、证据怎么算、系统怎么扩容而不漂移。
> 不包含任何具体领域的内容（数据、策略、结论）——机制与内容分离，是这个框架的第一原则。

An operating mechanism for multi-agent AI research collaboration: how to organize
agents so they **create new tools and new explanations** instead of re-running what
they already know — with anti-drift anchors, machine-checkable task flow, separated
authorship and review, and an evidence ledger that survives scaling.

---

## 它解决什么问题

单个 AI 会话做研究会自然滑向四个失败模式（这套机制就是为堵住它们而设计的）：

1. **任务漂移** — 做着做着就做歪了，离最初的问题越来越远。
2. **重复劳动** — 反复"验证"自己其实已经知道的东西；"可能知道、可能不知道"却不先问自己。
3. **半途而废 / 免检通过** — 遇到不行就放弃；做一下感觉可以就不验证，然后出 bug。
4. **加人不加速** — 人手变多只是提交变多，信息传递和审核成为瓶颈，吞吐不升反降。

## 核心想法

- **用智能，不用记忆**：代理的价值在于创造新的工具、理论和解释，而不是复现训练数据里的已知结论。
- **先有立得住的规则，再行动**：任何结论先写事前预测和判据，再看数据；没有规则不谈下注。
- **机制先于内容**：先把"怎么运作"理顺并固定下来，再开工做具体研究；机制本身有版本、有验收。
- **一切可核查**：任务有认领记录，交付有固定格式，结论有证据等级，失败完整保留。

## 机制地图

| 文档 | 内容 |
|---|---|
| [docs/01-philosophy.md](docs/01-philosophy.md) | 框架的四块：目标 / 工具 / 架构 / 经验；根本要求（三道死关） |
| [docs/02-architecture.md](docs/02-architecture.md) | 角色与会话：一会话一名字、单一接收口、作者不自审、双线对照 |
| [docs/03-workflow.md](docs/03-workflow.md) | 任务流：命题树 → 小叶拆分 → 认领板 → 交付块 → 复核 → 接收；定时叫醒与额度调度 |
| [docs/04-evidence.md](docs/04-evidence.md) | 证据纪律：事前预测、全局试验计数、暴露登记、已看方向标记、变异测试、前向验证 |
| [docs/05-uncertainty-and-tool-invention.md](docs/05-uncertainty-and-tool-invention.md) | 研究不确定性：为什么经典概率论不对题；先证可识别性边界，再发明新数学工具的流水线 |
| [docs/06-mechanism-assurance.md](docs/06-mechanism-assurance.md) | 机制的自我保证：活性（定时叫醒/漏接检测）、正确性、六种故障的恢复、防腐与降级模式 |
| [docs/07-tracker-and-snapshots.md](docs/07-tracker-and-snapshots.md) | 票据与快照：人类规模的工作迁入本地 tracker，为什么必须配快照回仓库；机器规模与人类规模的分层；关单单点的教训 |
| [templates/](templates/) | 可直接抄用的模板：认领卡、交付块、预登记页、工具卡、每日一页 |
| [reference/claimboard.py](reference/claimboard.py) | 认领板的最小参考实现（只追加日志 + 三值结局校验） |
| [agent/](agent/) | 整套机制的可运行参考实现（zero-dependency deep agent）：拆题派叶、复核复算、三态关单、票据与快照、互动控制台；模型后端可插拔，免 key 可跑演示 |

## 克隆并运行参考实现

```bash
git clone https://github.com/kkxiaoxi5/open-research-mechanism.git
cd open-research-mechanism/agent
./deploy.sh            # Linux/macOS（Windows 用 .\deploy.ps1；服务器用 docker compose up -d）
```

打开 `http://127.0.0.1:8765` 就是互动控制台（等你定 / 认领板 / 票据 / 成员 / 动态）。
零依赖，只需要 Python ≥ 3.11；默认演示后端免 key，接真模型见 `agent/README.md`。

## 快速开始

1. 读 `docs/01-philosophy.md`，把"根本要求"改成你自己项目的版本，单独存页。
2. 按 `docs/02-architecture.md` 给每个会话起唯一名字并登记名册。
3. 用 `templates/claim-card.md` 派第一张卡，要求交付时带 `templates/delivery-block.md`。
4. 审核与作者分离：任何产物必须由非作者复核后才算"已接收"。
5. 每天一页：开头先对"根本要求"，再写今天改变了哪个判断。

## 不是什么

- 不是某个领域的策略库或数据集（内容请放在你自己的私有仓库）。
- 不是提示词合集：提示词只是机制的载体之一，本仓库发布的是结构与规则。
- 不是全自动黑箱：关键判断（立项、升级证据、用不用结果）保留明确的人类决策点。

## License

MIT（见 [LICENSE](LICENSE)）。
