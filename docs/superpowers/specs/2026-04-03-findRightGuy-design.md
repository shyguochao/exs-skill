# findRightGuy Skill — 设计文档
> 生成日期：2026-04-03

## 项目定位

一个运行在 Claude Code 上的独立 Skill，通过分析用户与前任的聊天记录，识别触发用户正向情绪的对话特征，跨前任聚合提炼出"理想对象画像"，并提供三大功能：理想对象对话、恋爱模版导出、恋爱顾问。

---

## 一、整体架构

```
findRightGuy-skill/
├── SKILL.md                    # 主入口，命令路由 + 三大功能调度
│
├── prompts/                    # AI 推理模板层
│   ├── intake.md               # 信息录入（前任基本信息 + 聊天记录导入）
│   ├── emotion_analyzer.md     # 用户情绪信号识别规则（emoji/语气词/趋势判断）
│   ├── feature_extractor.md    # 从优质对话中提取前任特征（风格层 + 性格层）
│   ├── ideal_builder.md        # 跨前任聚合 → 生成理想对象画像
│   ├── ideal_persona.md        # 理想对象人格运行规则（对话 + 学习机制）
│   ├── template_builder.md     # 恋爱模版导出格式模板
│   └── advisor.md              # 恋爱顾问推理规则
│
├── tools/                      # Python 数据处理层
│   ├── wechat_parser.py        # 微信聊天记录解析
│   ├── qq_parser.py            # QQ 聊天记录解析
│   ├── emotion_scorer.py       # 用户情绪评分 + 优质对话片段标注
│   ├── feature_extractor.py    # 特征提取（高频行为/风格/性格维度）
│   ├── ideal_builder.py        # 跨前任聚合分析
│   ├── skill_writer.py         # Skill 文件管理（创建/合并/版本）
│   └── version_manager.py      # 版本存档与回滚
│
└── data/                       # 运行时产物（gitignored）
    ├── exes/                   # 各前任分析数据
    │   └── {slug}/
    │       ├── raw_analysis.md     # 情绪评分 + 优质对话片段
    │       ├── features.json       # 提取的特征数据
    │       └── memories/           # 原始素材
    ├── ideal/
    │   ├── SKILL.md            # 理想对象可运行 Skill
    │   ├── persona.md          # 理想对象人格
    │   ├── template.md         # 最新恋爱模版
    │   └── versions/           # 历史版本
    └── meta.json               # 全局元数据
```

**数据流向：**
```
原始聊天记录
  → emotion_scorer.py（情绪评分，标注优质对话片段）
  → feature_extractor.py（提取前任特征）
  → ideal_builder.py（跨前任聚合）
  → 生成 persona.md + template.md
  → SKILL.md 三大功能模块读取并运行
```

---

## 二、核心数据模型

### 2.1 情绪评分模型（emotion_scorer.py 输出）

```json
{
  "conversation_id": "wechat_2024_01",
  "ex_slug": "xiaoming",
  "total_messages": 1842,
  "analysis_period": ["2023-06-01", "2024-03-15"],
  "overall_emotion_curve": "wave",
  "segments": [
    {
      "segment_id": "seg_001",
      "time_range": ["2024-01-15 20:00", "2024-01-15 21:30"],
      "message_count": 86,
      "emotion_trend": "ascending",
      "peak_score": 8.5,
      "avg_score": 7.2,
      "is_quality": true,
      "trigger_message": "对方开启上升趋势的消息原文摘录",
      "peak_message": "情绪最高点时用户的回复",
      "user_signals": {
        "happy_emoji": ["😂", "🥰", "😊", "哈哈哈"],
        "happy_emoji_count": 12,
        "happy_emoji_trend": "increasing",
        "positive_particles": ["哈哈", "嗯嗯", "好呀", "真的吗"],
        "positive_particles_count": 18,
        "negative_particles": ["哦", "嗯", "随便"],
        "negative_particles_count": 2,
        "avg_reply_length": 42,
        "reply_length_trend": "up",
        "reply_speed_trend": "faster",
        "exclamation_count": 7,
        "question_count": 5,
        "initiative_count": 3
      },
      "conversation_sample": [
        {"sender": "ex", "text": "..."},
        {"sender": "user", "text": "..."}
      ]
    }
  ],
  "quality_segments": 23,
  "quality_ratio": 0.67,
  "best_time_slots": ["晚上8-11点", "周末下午"],
  "worst_time_slots": ["工作日午休"],
  "conversation_starters": {
    "effective": ["问你今天过得怎样", "分享有趣的事", "找你推荐"],
    "ineffective": ["单纯打招呼hi/在吗"]
  }
}
```

### 2.2 前任特征模型（features.json）

```json
{
  "slug": "xiaoming",
  "name": "小明",
  "relationship_duration": "1年3个月",
  "quality_segments_count": 23,
  "quality_ratio": 0.67,

  "style_features": {
    "humor": {
      "type": "自嘲式 + 情境幽默",
      "pattern": "用夸张比喻制造笑点，善用梗文化",
      "frequency": "high",
      "examples": ["原文举例1", "原文举例2"]
    },
    "topic_leading": {
      "style": "开放式提问引导深入，不停留表面",
      "depth": "high",
      "examples": ["你觉得这件事背后的原因是什么", "如果是你会怎么选"]
    },
    "reply_rhythm": {
      "speed": "非秒回",
      "quality": "内容丰富有质量",
      "avg_length": 68,
      "continuity": "善于接话，不冷场"
    },
    "empathy_expressions": ["原来如此", "听起来你那天很累", "这种感觉我懂", "辛苦了"],
    "compliment_style": "具体型，夸细节而非泛泛而谈",
    "conflict_style": "温和表达，不激化",
    "care_expressions": ["记住你说的小事并主动提起", "主动询问后续", "节假日主动问候"],
    "language_richness": "high",
    "storytelling_ability": "strong",
    "listening_signals": ["嗯嗯继续说", "然后呢", "真的假的详细说"]
  },

  "personality_features": {
    "initiative_score": 8,
    "emotional_stability_score": 7,
    "boundary_sense_score": 9,
    "empathy_score": 8,
    "humor_score": 9,
    "care_detail_score": 8,
    "patience_score": 7,
    "independence_score": 8,
    "attachment_style": "安全型",
    "love_language": ["精心的时刻", "肯定的言辞"],
    "mbti_inference": "ENFJ",
    "decision_style": "理性分析型，但尊重情感需求",
    "growth_mindset": true,
    "shared_interests_with_user": ["电影", "旅行", "美食探店"]
  },

  "interaction_patterns": {
    "best_conversation_types": [
      "分享日常趣事",
      "讨论未来计划",
      "互相吐槽",
      "深夜聊心里话"
    ],
    "your_happiest_triggers": [
      "主动分享他的生活",
      "记住你说过的事并提起",
      "用幽默化解你的低落",
      "给你具体的鼓励而非敷衍"
    ],
    "your_unhappy_triggers": [
      "话题戛然而止不接话",
      "只回复一两个字"
    ],
    "chemistry_score": 8.2
  }
}
```

### 2.3 理想对象画像模型（persona.md 结构）

```
# 理想对象画像 · v{n}

## Layer 0：硬规则（不可违背）
- 不说现实中不可能说的话
- 对话中发现用户情绪低落，优先关心而非继续话题
- 不强化不健康的执念
- 持续学习：每次对话后将触发用户正向情绪的自身行为记入 Correction 层

## Layer 1：身份锚定
- 融合来源：{前任A} × {前任B} × {前任C}
- MBTI 倾向：{推断值}
- 爱的语言：{主要类型}
- 关系风格：安全依恋型

## Layer 2：说话风格
- 幽默感：{风格描述 + 示例}
- 话题引导：{描述 + 示例}
- 回复节奏：{描述}
- 共情表达：{高频词汇列表}
- 关心细节：{描述 + 示例}
- 倾听信号：{描述}
- 示例对话：{3-5段真实融合样本}

## Layer 3：情感模式
- 情绪触发器（让用户开心的行为 TOP5）
- 主动性区间：{最优区间}
- 情绪稳定性：{描述}
- 深夜模式：{是否切换为更深入的聊天风格}

## Layer 4：关系行为
- 联系频率：{描述}
- 话题偏好：{列表}
- 边界感：{描述}

## Layer 5：Correction 记录（动态追加）
```

### 2.4 恋爱模版导出格式（template.md）

```markdown
# 我的理想对象模版 v{n}  ·  {导出日期}
> 基于 {n} 位前任的 {总优质对话片段数} 段优质对话分析生成

## 一、他是什么样的人
（综合性格画像，300字，覆盖性格特征、价值观、生活态度）

## 二、他怎么跟我说话
- 幽默感：...
- 话题引导方式：...
- 表达关心的方式：...
- 示例对话（3段）：...

## 三、让我最开心的行为 TOP10
| 排名 | 行为描述 | 来源前任 | 触发频率 |
|------|---------|---------|---------|

## 四、我的自我洞察
- 我在什么类型的对话中最快乐：...
- 我的情感需求核心：...
- 我容易被哪类表达打动：...
- 我的最佳互动时间段：...

## 五、红绿灯清单
### 🟢 绿灯特征
### 🟡 黄灯特征
### 🔴 红灯特征

## 六、各前任贡献图谱
| 前任 | 化学反应评分 | 主要贡献特征 | 优质对话占比 |
|------|------------|------------|------------|

## 七、给未来自己的话
（AI 基于数据生成的个性化建议）
```

---

## 三、三大功能模块

### 3.1 功能一：理想对象对话（/ideal-chat）

**运行流程：**
```
首次启动
  → 检查 data/ideal/persona.md 是否存在
  → 不存在：提示先运行 /analyze-ex 建立数据
  → 存在：加载 persona.md，进入对话模式

对话中：
  → AI 以 Layer 2 说话风格 + Layer 3 情感模式运行
  → 实时监测用户回复情绪信号（emoji/语气词/长度/速度）
  → 检测到正向信号 → 记录当前对方行为到候选 Correction 列表
  → 检测到负向信号 → 自动调整风格（降低幽默频率，增加共情表达）
  → 用户说"这句话很好/我喜欢这样" → 立即写入 Correction 层，永久生效

对话结束后（用户说"结束对话"）：
  → 自动将本次学习到的新行为 append 到 persona.md Layer 5
  → 更新 meta.json 中的 last_learned_at
```

### 3.2 功能二：恋爱模版导出（/export-template）

**运行流程：**
```
→ 读取 data/ideal/persona.md + 所有 data/exes/{slug}/features.json
→ 调用 template_builder.md 生成完整模版内容
→ 写入 data/ideal/template.md（带版本号和日期）
→ 同时存档到 data/ideal/versions/template_v{n}_{date}.md
→ 输出预览，询问用户是否需要调整某个章节
```

### 3.3 功能三：恋爱顾问（/advisor）

**场景 A：实时对话分析**
```
用户粘贴一段与新对象的聊天记录
  → AI 对照 data/ideal/persona.md 中的绿灯/红灯特征
  → 输出：
    ✅ 检测到绿灯特征：[具体行为]
    ⚠️  检测到黄灯特征：[具体行为]
    ❌ 检测到红灯特征：[具体行为]
    💡 建议：基于你的历史偏好，这种情况下可以这样回复...
```

**场景 B：主动咨询**
```
用户描述当前恋爱困惑
  → AI 基于 data/ideal/template.md 中的自我洞察数据
  → 结合用户历史"让你开心的行为 TOP10"
  → 给出个性化建议
```

### 3.4 数据建立主流程（/analyze-ex）

```
Step 1：信息录入（intake.md）
  → 前任代号/slug、关系时长、聊天记录来源

Step 2：聊天记录解析
  → 微信：wechat_parser.py
  → QQ：qq_parser.py

Step 3：情绪评分（emotion_scorer.py）
  → 逐段扫描用户情绪信号
  → 标注优质对话片段
  → 输出 raw_analysis.md

Step 4：特征提取（feature_extractor.py）
  → 从优质片段中提取前任说话风格 + 性格特征
  → 输出 features.json

Step 5：聚合更新（ideal_builder.py）
  → 将新前任特征与已有理想画像合并（加权融合）
  → 更新 data/ideal/persona.md
  → 版本存档

Step 6：输出分析摘要
  → 展示本次新增特征、化学反应评分、优质对话占比
```

---

## 四、情绪评分算法

### 信号权重配置

```python
EMOTION_WEIGHTS = {
    "happy_emoji":        3.0,   # 😂🥰😊 等强正向 emoji
    "positive_particles": 1.5,   # 哈哈/嗯嗯/好呀
    "exclamation":        1.0,   # 感叹号
    "question":           1.2,   # 主动追问（参与度信号）
    "reply_length_up":    2.0,   # 回复变长（投入度上升）
    "reply_speed_up":     1.8,   # 回复变快
    "initiative":         2.5,   # 用户主动发起新话题
    "negative_emoji":    -3.0,   # 😒🙄 等负向 emoji
    "negative_particles":-2.0,   # 哦/嗯/随便
    "reply_length_down": -1.5,   # 回复变短
}
```

### 优质对话判定规则（同时满足）

```python
QUALITY_RULES = {
    "min_avg_score": 6.0,          # 平均情绪分 ≥ 6
    "trend": "ascending",          # 整体趋势必须上升
    "min_duration_messages": 20,   # 至少持续 20 条消息
    "peak_score": 7.5,             # 峰值分 ≥ 7.5
}
```

### 跨前任加权融合规则

```
各前任特征贡献权重 = 化学反应评分 × 优质对话比例

冲突特征处理：
若两前任在同一维度得分差异 > 3，标注为 [⚠️ 偏好未定]，
向用户展示两种风格样本，让用户选择偏好
```

### 理想对象学习机制

```
每轮对话结束时：
1. 统计本轮用户情绪曲线
2. 找出情绪峰值前 3 条对方消息
3. 提取这 3 条消息的表达特征
4. 与现有 Layer 5 Correction 去重后追加
5. 更新 meta.json 的 learned_behaviors_count

每累计 10 次学习 → 触发 persona.md 重新聚合
（将 Layer 5 高频 Correction 升级到 Layer 2/3 正式层）
```

---

## 五、完整命令清单

| 命令 | 功能 |
|------|------|
| `/analyze-ex` | 导入新前任，更新理想画像 |
| `/ideal-chat` | 与理想对象对话 |
| `/export-template` | 导出最新恋爱模版 |
| `/advisor` | 恋爱顾问模式 |
| `/show-profile` | 查看当前理想对象画像摘要 |
| `/list-exes` | 查看已录入的所有前任及贡献图谱 |
| `/rollback {version}` | 回滚到历史版本的理想画像 |

---

## 六、版本管理策略

```
每次 /analyze-ex 完成后 → 自动备份当前 ideal/ 快照
每次 /export-template → 存档带日期版本的 template
每次对话学习满 10 条 → 自动备份 persona.md

版本命名格式：
  persona_v{n}_{YYYYMMDD}.md
  template_v{n}_{YYYYMMDD}.md

保留最近 10 个版本，更早的自动清理
```
