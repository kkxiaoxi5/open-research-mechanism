# Changelog

## 0.7.1 — 2026-11-15

- 防呆：控制台副标题显示 agent 版本号（`/api/state` 带 version），
  一眼可辨自己看的是不是新版；`deploy.sh` / `deploy.ps1` 启动前
  检查端口占用——旧服务还占着 8765 时明确报错并给停法，不再出现
  「部署了却没变化」（新进程抢不到端口、浏览器还连着旧服务）。

## 0.7.0 — 2026-11-15

- 控制台按用户反馈重做（agent 包 0.4.0）：
  - **成员管理**：新增 `registry.py` 成员注册表——UI 里增删 agent、
    逐个设模型参数（model / base_url / temperature / 启用；API key
    只存环境变量名），协调者每轮按注册表重建工作队（新成员下轮即上工）。
  - **关系图**：按真实事件（派工/交付/关单/对话/回复）生成的连线图，
    边带次数，不再靠猜谁和谁在交互。
  - **持久会话 + 现代布局**：左侧任务管理栏（等你定/认领板/票据/
    成员/关系图），中间聊天栏按成员分频道，会话存 `chat.jsonl`
    持久保存；右侧 **Prompt 导航**列出全部消息节点，点任意节点即
    定位并设为分叉点，下一条消息从该处长出新分支（parent 指针，
    原线保留）。叫醒一轮后，各成员会在自己频道里按真实工作记录
    回复（接真模型时由其模型直接作答）。
- 测试增至 10 个，全过；deploy.sh 实测新增成员当轮上工、聊天回复、
  关系图边均正确。

## 0.6.2 — 2026-11-15

- 修复 Windows 上无法启动：`board.py` 的文件锁改跨平台（POSIX 用
  fcntl、Windows 用 msvcrt），此前在 Windows 克隆运行 deploy.ps1 时
  `import fcntl` 直接崩。新增回归测试（屏蔽 fcntl + 桩 msvcrt 验证
  Windows 分支可导入可写）。`deploy.ps1` 增加退出码检查，Python
  步骤失败时不再误报成功。agent 包 0.3.1。

## 0.6.1 — 2026-11-15

- 三语主 README 与 agent README 补上克隆指令（git clone + cd agent +
  deploy），主 README 新增「克隆并运行参考实现」一节。

## 0.6.0 — 2026-11-15

- `agent/` 互动控制台上线（`webapp.py`，agent 包 0.3.0）：五视图
  （等你定 / 认领板 / 票据 / 成员 / 动态）+ 五个操作（开叶子、建票据、
  决定票据、给成员发消息、叫醒一轮）。所有写入经 Board/Tickets 同一套
  规则校验，无直写后门；用户直达消息经 inbox 在叫醒轮送达对应 worker。
  `serve` 命令改走控制台（新增 `--host`）。
- 一键部署：`deploy.sh`（Linux/macOS）、`deploy.ps1`（Windows）、
  `Dockerfile` + `docker-compose.yml`（服务器，状态存 volume）。
- 测试增至 8 个（含 webapp 的 HTTP 全流程），全过；deploy.sh 实测
  启动→叫醒一轮（3 证成 / 1 证否 / 1 拆小）→开叶子→停机全通。

## 0.5.1 — 2026-11-15

- 新增捆绑 skill `tracker-workflow`（票据/MR/认领板的映射、token 只存
  server、MCP 的适用边界、关单纪律），skills 共 7 个，测试同步更新。
- `agent/PLAN.md` 登记两项决定：②票据用外挂 tracker（Gitea 可，
  TrackerAdapter 接口，GitLab 为第二适配器；服务端走 REST API，
  MCP 仅供外部对话壳代理）；④UI 为必需且可互动（经 server 校验写入）。

## 0.5.0 — 2026-11-15

- `agent/` 捆绑六个必需 skills（`agent/skills/`，标准 SKILL.md 格式）：
  leaf-splitting（拆叶）、known-answer-tests（已知答案测试）、
  counterexample-hunting（反例猎杀）、proof-review（证明复核）、
  formalization（形式化）、evidence-accounting（证据记账）。
  新增 `skills.py` 加载器（按角色注入提示词）与 `skills` 命令；
  agent 包版本升至 0.2.0；测试增至 5 个，全过。

## 0.4.3 — 2026-11-15

- `agent/PLAN.md` 登记用户决定：主场景为**数学研究**（待决③关闭）。
  v0.2 演示题改为数学命题集；检查器生态向证明检查与符号复算扩展；
  对话分叉优先级上调、per-worker 代码工作区优先级下调。

## 0.4.2 — 2026-11-15

- 新增 `agent/PLAN.md`：v0.2–v0.5 计划书（Swarm 式协作对标 Antigravity /swarm、
  Claude Code 式对话与任务分支 UI、Docker 服务端部署；含分期验收与
  「对话可分支、台账不可分支」的硬取舍）。三份 agent README 加路线图链接。

## 0.4.1 — 2026-11-15

- 三语文档：主 README 新增英文版 `README.en.md` 与日文版 `README.ja.md`；
  `agent/README` 补齐简体中文版与日文版；四份 README 顶部互加语言切换链接。
  （docs/ 正文的三语化为后续工作。）

## 0.4.0 — 2026-11-15

- 新增 `agent/`：整套机制的可运行参考实现（deep-agent 形态，零依赖标准库）：
  认领板三态关单、作者/复核分离、协调者叫醒循环、可插拔模型后端
  （mock 免 key 演示 + OpenAI 兼容接口）、人类规模票据与快照导出、
  只读可视化看板；附演示题（一次跑通证成/证否/拆小）与单元测试。

## 0.3.0 — 2026-11-15

- 新增 `docs/07-tracker-and-snapshots.md`：票据与快照
  （人类规模工作迁入本地部署 tracker 的理由；状态以快照回仓库以保住
  开机读文件与备份纪律；机器/人类两层分开；关单单点的失败教训；试点对账）。

## 0.2.0 — 2026-11-15

- 新增 `docs/05-uncertainty-and-tool-invention.md`：研究不确定性的方法与工具发明流水线
  （可识别性先行、最小合成世界、形式化放大、负结果记账）。
- 新增 `docs/06-mechanism-assurance.md`：机制的自我保证
  （活性 / 正确性 / 六种故障恢复 / 防腐与降级模式 / 每周自检表）。

## 0.1.0 — 2026-11-15

- 首个公开版本：从一个私有研究项目的协作实践中抽离机制层。
- README（中英）、哲学（四块 + 根本要求三道死关）、架构（角色与信息流）、
  工作流（命题 → 小叶 → 认领板 → 交付块 → 复核 → 收口）、证据纪律（分层与五条硬规则）。
- 模板五份：认领卡、交付块、预登记页、工具卡、每日一页。
- 参考实现：`reference/claimboard.py`（只追加日志 + 三值结局强制）。
