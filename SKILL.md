---
name: findRightGuy
description: 通过分析与前任的聊天记录，提炼理想对象画像，提供对话模拟、恋爱模版导出和恋爱顾问三大功能
version: v1.0
allowed-tools: Read, Write, Edit, Bash
---

# findRightGuy Skill

## 命令路由

| 命令 | 功能 | 工具 |
|------|------|------|
| `/analyze-ex` | 导入新前任，更新理想画像 | 见下方主流程 |
| `/ideal-chat` | 与理想对象 AI 对话 | Read: data/ideal/persona.md |
| `/export-template` | 导出最新恋爱模版 | Bash: skill_writer + template_builder |
| `/advisor` | 恋爱顾问模式 | Read: data/ideal/template.md |
| `/show-profile` | 查看理想对象画像摘要 | Read: data/ideal/persona.md |
| `/list-exes` | 查看所有前任及贡献图谱 | Bash: skill_writer --action list |
| `/rollback {version}` | 回滚到历史版本 | Bash: version_manager --action rollback |

---

## /analyze-ex — 数据建立主流程

### Step 1：信息录入

读取 `prompts/intake.md`，按照其中的 Q1/Q2/Q3 向用户提问，收集：
- 前任代号（slug）
- 基本信息（相处时长、职业、城市）
- 聊天记录来源类型

### Step 2：初始化目录

```bash
python3 ${SKILL_DIR}/tools/skill_writer.py \
  --action init \
  --slug {slug} \
  --data-dir ${SKILL_DIR}/data/exes
```

### Step 3：聊天记录解析

**微信聊天记录：**
```bash
python3 ${SKILL_DIR}/tools/wechat_parser.py \
  --file {用户提供的文件路径} \
  --target {前任名字} \
  --output ${SKILL_DIR}/data/exes/{slug}/parsed.json
```

**QQ 聊天记录：**
```bash
python3 ${SKILL_DIR}/tools/qq_parser.py \
  --file {用户提供的文件路径} \
  --target {前任名字} \
  --output ${SKILL_DIR}/data/exes/{slug}/parsed.json
```

**口述 / 截图：** 由 AI 直接根据用户描述生成结构化 parsed.json，跳过脚本解析。

### Step 4：情绪评分

```bash
python3 ${SKILL_DIR}/tools/emotion_scorer.py \
  --input ${SKILL_DIR}/data/exes/{slug}/parsed.json \
  --user {用户自己的名字/昵称} \
  --output ${SKILL_DIR}/data/exes/{slug}/raw_analysis.json
```

参考 `prompts/emotion_analyzer.md` 理解评分逻辑。

### Step 5：特征提取

```bash
python3 ${SKILL_DIR}/tools/feature_extractor.py \
  --analysis ${SKILL_DIR}/data/exes/{slug}/raw_analysis.json \
  --parsed ${SKILL_DIR}/data/exes/{slug}/parsed.json \
  --slug {slug} \
  --name {前任姓名} \
  --output ${SKILL_DIR}/data/exes/{slug}/features.json
```

参考 `prompts/feature_extractor.md` 理解特征维度。

### Step 6：跨前任聚合

```bash
python3 ${SKILL_DIR}/tools/ideal_builder.py \
  --data-dir ${SKILL_DIR}/data/exes \
  --output-dir ${SKILL_DIR}/data/ideal
```

参考 `prompts/ideal_builder.md` 理解融合规则。

### Step 7：版本备份 + 生成 SKILL.md

```bash
python3 ${SKILL_DIR}/tools/version_manager.py \
  --action backup \
  --output-dir ${SKILL_DIR}/data/ideal

python3 ${SKILL_DIR}/tools/skill_writer.py \
  --action combine \
  --output-dir ${SKILL_DIR}/data/ideal
```

### Step 8：输出分析摘要

向用户展示：
- 本次分析的优质对话片段数量和占比
- 化学反应评分
- 新增了哪些核心特征
- 当前理想画像的版本号

---

## /ideal-chat — 理想对象对话模式

### 启动检查

1. 读取 `data/ideal/persona.md`，若不存在则提示：「请先运行 /analyze-ex 建立数据基础」
2. 加载 persona.md 中的 Layer 0-6 全部内容

### 运行规则

严格按照 `prompts/ideal_persona.md` 中定义的规则运行：
- Layer 0 硬规则优先级最高，永远不违背
- 使用 Layer 2 的说话风格（口头禅/emoji/幽默频率）
- 实时感知用户情绪信号，动态调整互动风格

### 学习触发词

- 「这句话很好」「我喜欢这样」「你这样让我很开心」→ 记录当前行为
- 「不对」「你不会这样说」「这不像你」→ 调整行为，记录错误

### 结束对话

当用户说「结束」「拜拜」「下次再聊」等结束意图时：
1. 提取本次情绪峰值前的 3 条发言特征
2. 写入 persona.md Layer 6（Correction 追加区）：

```bash
# 将学习内容 append 到 persona.md
# AI 直接使用 Edit 工具写入 Layer 6 区域
```

3. 若 Layer 6 累计超过 10 条，提示用户重新聚合

---

## /export-template — 恋爱模版导出

### 执行流程

1. 读取 `data/ideal/persona.md` 和所有 `data/exes/*/features.json`
2. 读取 `prompts/template_builder.md` 获取七章节生成规范
3. AI 根据规范生成完整模版内容
4. 写入文件：

```bash
# 写入当前版本
# output: data/ideal/template.md

# 同时写入版本存档
# output: data/ideal/versions/template_v{n}_{YYYYMMDD}.md
```

5. 在终端展示模版预览（前200字），询问是否需要调整某章节

---

## /advisor — 恋爱顾问模式

### 启动时询问场景

> 你想要：
> A. 分析一段聊天记录（粘贴你和新对象的对话）
> B. 咨询一个恋爱问题

### 场景 A：实时对话分析

1. 用户粘贴聊天记录
2. 读取 `data/ideal/persona.md` 的 Layer 3/4（绿灯/红灯特征）
3. 按照 `prompts/advisor.md` 的场景A规范进行分析
4. 输出绿/黄/红灯分类报告 + 综合建议

### 场景 B：主动咨询

1. 理解用户描述的困惑
2. 读取 `data/ideal/template.md` 的「自我洞察」和「红绿灯清单」
3. 按照 `prompts/advisor.md` 的场景B规范给出个性化建议

---

## /show-profile — 理想对象画像摘要

读取 `data/ideal/persona.md`，提取并展示：
- 当前版本号和生成日期
- 数据来源（几位前任）
- 各维度评分雷达图（文字版）
- 让你最开心的行为 Top5
- 当前 Correction 学习记录数量

---

## /list-exes — 前任列表

```bash
python3 ${SKILL_DIR}/tools/skill_writer.py \
  --action list \
  --data-dir ${SKILL_DIR}/data/exes
```

---

## /rollback {version} — 版本回滚

```bash
python3 ${SKILL_DIR}/tools/version_manager.py \
  --action rollback \
  --output-dir ${SKILL_DIR}/data/ideal \
  --version {version}
```

如未指定 version，先运行：
```bash
python3 ${SKILL_DIR}/tools/version_manager.py \
  --action list \
  --output-dir ${SKILL_DIR}/data/ideal
```
展示版本列表，让用户选择。

---

## 工具降级策略

若 Bash 工具执行失败（权限问题/环境问题）：
1. 提示用户手动执行对应命令
2. AI 读取现有 JSON 文件，尝试用 Write/Edit 工具直接生成目标文件
3. 记录降级原因，建议用户修复环境后重新运行
