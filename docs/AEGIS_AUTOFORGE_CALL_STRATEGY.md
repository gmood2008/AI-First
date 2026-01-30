# AutoForge 能力与调用策略说明（Aegis 视角）

## 文档目的

本文件用于明确：

- AutoForge 的核心能力边界
- Aegis 在不同阶段如何、是否、以何种方式调用 AutoForge
- AutoForge 对系统安全模型的影响（联网 / 依赖 / 写仓库）

从而为 AI-First、k-os、ascend-ai 提供一致、不可误解的实现依据。

---

## 一、AutoForge 是什么（能力定义）

AutoForge 是 Aegis 体系中的「智能构建引擎」，负责把“意图”转化为“可执行、可治理的系统资产”。

它不是单一的“代码生成器”，而是一个多形态产物生成系统。

---

## 二、AutoForge 的主要能力（能力分层）

### 2.1 能力总览（结论先行）

AutoForge 的核心能力包括：

- Workflow / 执行结构生成
- Pack / Asset 生成
- Facade / API 抽象生成
- 代码生成（受约束）
- 脚手架与模板渲染
- 动态修复与补丁生成（Hotfix）

AutoForge 不直接执行、不调度、不授权，只“构建”。

### 2.2 具体能力拆解

#### 1 Workflow 生成（结构级）

- 输入：Quest / 用户意图
- 输出：WorkflowSpec

能力特征：

- 描述步骤、依赖、条件、分支
- 不包含具体实现细节
- 是规划级产物

用于回答 “我要做什么”，而不是 “怎么跑代码”。

#### 2 Pack / Asset 生成（可执行单元）

输出内容可能包括：

- Skill Pack
- Script Pack
- Tool Definition
- Config / Policy

特征：

- 可被 ascend-ai / k-os 加载
- 必须具备：
  - 明确权限声明
  - 可版本化
  - 可回滚

#### 3 Facade / 接口抽象生成

AutoForge 可生成：

- Facade API
- Tool Interface
- 统一调用入口

目的：

- 隔离实现变化
- 稳定上层调用
- 支持 Teaching Mode / Skill 演进

#### 4 代码生成（受限能力）

AutoForge 可以生成代码，但必须满足：

- 有上下文（Workflow / Pack / Facade）
- 有 Constitution 约束
- 有 Diff + Explanation

不允许“无上下文裸写代码”。

#### 5 脚手架与模板渲染

用于：

- 标准 Skill 初始化
- Pack 结构生成

模板必须：

- 可审计
- 可版本化
- 不包含隐式副作用

#### 6 动态修复 / Hotfix 生成

- 输入：
  - Execution Snapshot
  - 错误上下文
  - Skill Memory
- 输出：
  - 最小侵入 Patch

约束：

- 必须可回滚
- 必须经过 Handshake（如涉及权限变化）

---

## 三、Aegis 在什么阶段调用 AutoForge？

这是系统设计的关键问题，直接决定 AutoForge 的安全边界。

### 3.1 阶段一：规划前（Quest → WorkflowSpec）

是否调用 AutoForge：是（核心场景）

调用目的：

- 把模糊意图结构化
- 形成可验证的执行蓝图

特点：

- 不生成可执行代码
- 不触碰系统资源
- 纯“规划智能”

这是最低风险、最高价值阶段。

### 3.2 阶段二：执行前（生成 Pack / Asset）

是否调用 AutoForge：是（受控场景）

调用目的：根据 WorkflowSpec 生成：

- Skill Pack
- Script
- Facade

关键约束：

- 必须在 PROVISIONAL 状态
- 必须通过 Constitution 校验
- 不得直接写入生产仓库

这是 Handshake 之前的准备阶段。

### 3.3 阶段三：执行中（动态生成 / 修复）

是否调用 AutoForge：是（严格受限）

适用场景：

- 执行失败
- 环境变化
- 小范围行为修正

强制限制：

- 禁止结构性重写
- 禁止权限升级
- 仅允许：
  - Hotfix
  - 参数修正
  - 逻辑补丁

并且：

- 必须产生 Execution Snapshot
- 必须可回滚

执行中调用是“外科手术”，不是“再造系统”。

---

## 四、AutoForge 是否需要联网 / 拉依赖 / 写仓库？

### 4.1 结论先行（强约束）

默认：不允许。

AutoForge 在 Aegis 体系中的默认策略是：

| 能力 | 是否允许 | 说明 |
| --- | --- | --- |
| 联网 | 默认禁止 | 除非显式授予 |
| 拉外部依赖 | 禁止 | 防止供应链污染 |
| 写入生产仓库 | 禁止 | 必须通过 Handshake |
| 写临时沙箱 | 允许 | 用于生成与验证 |

### 4.2 为什么必须这样设计？

- 安全性
  - 防止 Prompt → 外部代码执行
  - 防止隐式依赖注入
  - 防止模型“自我扩展能力”
- 可治理性
  - 所有产物必须可审计、可复现、可删除
- 信任模型
  - 用户信任的是 Aegis，而不是 AutoForge

### 4.3 例外机制（必须显式）

如需：联网 / 拉依赖 / 写入仓库，则必须：

- 由 Aegis 发起授权
- 明确 scope / 时限
- 进入 PROVISIONAL → Handshake 流程

---

## 五、总结（一句话版）

- AutoForge 是“构建智能”，不是“执行智能”
- Aegis 在规划前、执行前、执行中均可调用 AutoForge，但权限逐级收紧
- AutoForge 默认是离线、隔离、不可写入生产的

最终定位一句话：

AutoForge 负责“怎么造”，Aegis 负责“能不能用、敢不敢用、什么时候用”。
