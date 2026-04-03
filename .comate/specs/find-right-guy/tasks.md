# findRightGuy Skill 实现计划

- [ ] Task 1: 搭建项目基础结构
    - 1.1: 创建完整目录结构（prompts/、tools/、data/）
    - 1.2: 创建 requirements.txt（Pillow、chardet、python-dateutil）
    - 1.3: 创建 .gitignore（忽略 data/ 目录）
    - 1.4: 创建 README.md（项目说明、安装步骤、命令清单）

- [ ] Task 2: 实现聊天记录解析工具
    - 2.1: 从参考项目拷贝 wechat_parser.py，适配本项目输出格式
    - 2.2: 从参考项目拷贝 qq_parser.py，适配本项目输出格式
    - 2.3: 验证解析器输出结构符合 emotion_scorer.py 的输入要求

- [ ] Task 3: 实现情绪评分核心引擎（emotion_scorer.py）
    - 3.1: 实现情绪信号权重配置（EMOTION_WEIGHTS）
    - 3.2: 实现逐消息情绪打分函数 score_message()
    - 3.3: 实现对话分段函数 segment_conversation()（按时间间隔 > 2小时切割）
    - 3.4: 实现片段情绪趋势判断函数 calc_trend()（ascending/stable/descending）
    - 3.5: 实现优质对话判定函数 is_quality_segment()（QUALITY_RULES 四条件）
    - 3.6: 实现 best_time_slots 和 conversation_starters 统计
    - 3.7: 实现 CLI 接口，输出完整 raw_analysis.json

- [ ] Task 4: 实现特征提取工具（feature_extractor.py）
    - 4.1: 实现从优质对话片段中提取说话风格特征（humor/topic_leading/reply_rhythm/empathy）
    - 4.2: 实现性格维度评分（initiative/emotional_stability/empathy 等8个维度）
    - 4.3: 实现 interaction_patterns 提取（best_conversation_types/happiest_triggers）
    - 4.4: 实现 chemistry_score 计算（综合评分）
    - 4.5: 输出标准 features.json

- [ ] Task 5: 实现跨前任聚合分析工具（ideal_builder.py）
    - 5.1: 实现加权融合算法（权重 = chemistry_score × quality_ratio）
    - 5.2: 实现冲突特征检测（同维度差异 > 3 → 标注 ⚠️ 偏好未定）
    - 5.3: 实现 persona.md 生成（Layer 0-5 完整结构）
    - 5.4: 实现增量 merge 逻辑（新增前任时追加而非覆盖）
    - 5.5: 输出聚合摘要（新增特征列表、各前任贡献权重）

- [ ] Task 6: 实现 Skill 文件管理工具（skill_writer.py）
    - 6.1: 实现 init action（创建 data/exes/{slug}/ 标准目录结构）
    - 6.2: 实现 combine action（读取 persona.md 生成可运行 ideal/SKILL.md）
    - 6.3: 实现 list action（列出所有前任及化学反应评分、优质对话占比）

- [ ] Task 7: 实现版本管理工具（version_manager.py）
    - 7.1: 实现 backup action（快照 persona.md/template.md/meta.json）
    - 7.2: 实现 rollback action（还原前先备份当前版本）
    - 7.3: 实现 list action（展示历史版本列表）
    - 7.4: 实现自动清理（保留最近 10 个版本）

- [ ] Task 8: 编写 AI Prompt 模板层
    - 8.1: 编写 intake.md（3问信息录入脚本：slug/基本信息/聊天来源）
    - 8.2: 编写 emotion_analyzer.md（情绪信号识别规则，指导 AI 理解评分逻辑）
    - 8.3: 编写 feature_extractor.md（特征提取维度定义 + 标签翻译表）
    - 8.4: 编写 ideal_builder.md（跨前任聚合规则 + 冲突处理逻辑）
    - 8.5: 编写 ideal_persona.md（理想对象 Layer 0-5 运行规则 + 学习机制）
    - 8.6: 编写 template_builder.md（恋爱模版七章节生成模板）
    - 8.7: 编写 advisor.md（顾问模式推理规则：绿灯/黄灯/红灯识别 + 建议生成）

- [ ] Task 9: 编写主 SKILL.md
    - 9.1: 编写 frontmatter（name/description/version/allowed-tools）
    - 9.2: 编写命令路由表（7个命令 → 对应工具和 prompt）
    - 9.3: 编写 /analyze-ex 完整 6 步流程
    - 9.4: 编写 /ideal-chat 对话模式（加载 persona + 实时情绪监测 + 学习机制）
    - 9.5: 编写 /export-template 导出流程
    - 9.6: 编写 /advisor 两种场景（实时分析 + 主动咨询）
    - 9.7: 编写管理命令（/show-profile、/list-exes、/rollback）

- [ ] Task 10: 集成验证与收尾
    - 10.1: 端到端验证 /analyze-ex 流程（模拟聊天数据 → 生成 features.json）
    - 10.2: 验证 /ideal-chat 命令可正常加载 persona.md 并进入对话
    - 10.3: 验证 /export-template 生成完整七章节模版
    - 10.4: 验证 /advisor 能正确识别绿灯/红灯特征
    - 10.5: 推送所有代码到 GitHub 远程仓库
