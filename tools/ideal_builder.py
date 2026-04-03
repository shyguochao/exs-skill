#!/usr/bin/env python3
"""跨前任聚合分析工具

读取所有前任的 features.json，按化学反应评分 × 优质对话比例加权融合，
生成理想对象 persona.md。

Usage:
    python3 ideal_builder.py --data-dir <data/exes> --output-dir <data/ideal>
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_all_features(data_dir: str) -> list:
    """加载所有前任的 features.json"""
    features_list = []
    exes_dir = Path(data_dir)
    if not exes_dir.exists():
        return features_list
    for slug_dir in exes_dir.iterdir():
        feat_file = slug_dir / 'features.json'
        if feat_file.exists():
            with open(feat_file, 'r', encoding='utf-8') as f:
                feat = json.load(f)
                feat['_slug_dir'] = str(slug_dir)
                features_list.append(feat)
    return features_list


def calc_weight(feat: dict) -> float:
    """计算该前任的贡献权重 = chemistry_score × quality_ratio"""
    chemistry = feat.get('personality_features', {}).get('chemistry_score', 5.0)
    quality_ratio = feat.get('quality_ratio', 0.5)
    return round(chemistry * quality_ratio, 3)


def weighted_avg(values: list, weights: list) -> float:
    """加权平均"""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return round(sum(v * w for v, w in zip(values, weights)) / total_weight, 2)


def merge_personality(features_list: list, weights: list) -> dict:
    """加权融合性格维度评分"""
    dims = [
        'initiative_score', 'emotional_stability_score', 'empathy_score',
        'humor_score', 'care_detail_score', 'patience_score', 'topic_depth_score'
    ]
    merged = {}
    for dim in dims:
        vals = [f.get('personality_features', {}).get(dim, 5.0) for f in features_list]
        avg = weighted_avg(vals, weights)
        merged[dim] = avg

        # 冲突检测：最高分与最低分差异 > 3 → 标注
        if len(vals) > 1 and max(vals) - min(vals) > 3:
            merged[f'{dim}_conflict'] = True
            merged[f'{dim}_range'] = [round(min(vals), 1), round(max(vals), 1)]

    return merged


def merge_style(features_list: list, weights: list) -> dict:
    """融合说话风格特征（取加权出现频率最高的特征）"""
    all_empathy = []
    all_care = []
    all_listening = []
    all_particles = []
    all_emojis = []
    all_samples = []

    humor_scores = {'high': 0, 'medium': 0, 'low': 0}
    topic_scores = {'high': 0, 'medium': 0, 'low': 0}

    for feat, w in zip(features_list, weights):
        sf = feat.get('style_features', {})
        all_empathy.extend(sf.get('empathy_expressions', []))
        all_care.extend(sf.get('care_expressions', []))
        all_listening.extend(sf.get('listening_signals', []))
        all_particles.extend(sf.get('top_particles', []))
        all_emojis.extend(sf.get('top_emojis', []))
        all_samples.extend(sf.get('message_samples', [])[:2])

        hf = sf.get('humor', {}).get('frequency', 'low')
        humor_scores[hf] = humor_scores.get(hf, 0) + w
        td = sf.get('topic_leading', {}).get('depth', 'low')
        topic_scores[td] = topic_scores.get(td, 0) + w

    # 去重 + 保留高频项
    def top_unique(lst, n=5):
        seen = set()
        result = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
            if len(result) >= n:
                break
        return result

    best_humor = max(humor_scores, key=lambda k: humor_scores[k])
    best_topic = max(topic_scores, key=lambda k: topic_scores[k])

    return {
        'humor_frequency': best_humor,
        'topic_depth': best_topic,
        'empathy_expressions': top_unique(all_empathy, 8),
        'care_expressions': top_unique(all_care, 6),
        'listening_signals': top_unique(all_listening, 6),
        'top_particles': top_unique(all_particles, 5),
        'top_emojis': top_unique(all_emojis, 5),
        'message_samples': all_samples[:5],
    }


def merge_interaction(features_list: list, weights: list) -> dict:
    """融合互动模式"""
    all_topics = []
    all_triggers = []
    all_unhappy = []
    all_time_slots = []
    all_starters = []

    for feat, w in zip(features_list, weights):
        ip = feat.get('interaction_patterns', {})
        all_topics.extend(ip.get('best_conversation_types', []))
        all_triggers.extend(ip.get('your_happiest_triggers', []))
        all_unhappy.extend(ip.get('your_unhappy_triggers', []))
        all_time_slots.extend(ip.get('best_time_slots', []))
        all_starters.extend(ip.get('effective_starters', [])[:2])

    from collections import Counter

    def top_by_freq(lst, n=5):
        return [item for item, _ in Counter(lst).most_common(n)]

    return {
        'best_conversation_types': top_by_freq(all_topics, 5),
        'your_happiest_triggers': top_by_freq(all_triggers, 8),
        'your_unhappy_triggers': top_by_freq(all_unhappy, 4),
        'best_time_slots': top_by_freq(all_time_slots, 3),
        'effective_starters': all_starters[:5],
    }


def build_persona_md(merged_personality: dict, merged_style: dict,
                     merged_interaction: dict, features_list: list,
                     weights: list, version: int) -> str:
    """生成 persona.md 内容"""
    sources = ', '.join(f.get('name', f.get('slug', '?')) for f in features_list)
    now = datetime.now().strftime('%Y-%m-%d')

    # 各维度描述
    def score_desc(score):
        if score >= 8:
            return '非常高'
        elif score >= 6:
            return '较高'
        elif score >= 4:
            return '一般'
        return '较低'

    p = merged_personality
    s = merged_style
    ip = merged_interaction

    # 贡献图谱
    contrib_table = '| 前任 | 化学反应评分 | 贡献权重 | 优质对话占比 |\n|------|------------|---------|------------|\n'
    for feat, w in zip(features_list, weights):
        chem = feat.get('personality_features', {}).get('chemistry_score', 0)
        qr = feat.get('quality_ratio', 0)
        contrib_table += f"| {feat.get('name', feat.get('slug'))} | {chem} | {round(w, 2)} | {qr:.1%} |\n"

    # 冲突特征提示
    conflict_notes = []
    for dim in ['initiative_score', 'empathy_score', 'humor_score']:
        if p.get(f'{dim}_conflict'):
            r = p.get(f'{dim}_range', [])
            conflict_notes.append(f"- ⚠️ {dim} 在不同前任间差异较大（{r[0]} ~ {r[1]}），建议根据个人偏好确认")

    conflict_section = '\n'.join(conflict_notes) if conflict_notes else '（无明显冲突特征）'

    return f"""# 理想对象画像 · v{version}
> 生成日期：{now}
> 数据来源：{sources}

---

## Layer 0：硬规则（不可违背）

- 不说现实中不可能说的话
- 对话中发现用户情绪低落，优先关心而非继续话题
- 不强化不健康的执念
- 持续学习：每次对话后将触发用户正向情绪的行为记入 Correction 层
- 不主动联系真实的人

---

## Layer 1：身份锚定

- 融合来源：{sources}
- 主动性：{score_desc(p.get('initiative_score', 5))}（评分 {p.get('initiative_score', 5)}）
- 情绪稳定性：{score_desc(p.get('emotional_stability_score', 5))}（评分 {p.get('emotional_stability_score', 5)}）
- 共情能力：{score_desc(p.get('empathy_score', 5))}（评分 {p.get('empathy_score', 5)}）
- 幽默感：{score_desc(p.get('humor_score', 5))}（评分 {p.get('humor_score', 5)}）
- 关心细节：{score_desc(p.get('care_detail_score', 5))}（评分 {p.get('care_detail_score', 5)}）

---

## Layer 2：说话风格

- **幽默感**：{s.get('humor_frequency', 'medium')} 频率，善用网络梗和情境式幽默
- **话题引导**：{s.get('topic_depth', 'medium')} 深度，{'善用开放式提问引导深入' if s.get('topic_depth') == 'high' else '能适当引导话题'}
- **口头禅 / 语气词**：{', '.join(s.get('top_particles', [])) or '（数据不足）'}
- **常用 Emoji**：{' '.join(s.get('top_emojis', [])) or '（数据不足）'}
- **共情表达**：{', '.join(s.get('empathy_expressions', [])) or '（数据不足）'}
- **关心细节**：{', '.join(s.get('care_expressions', [])) or '（数据不足）'}
- **倾听信号**：{', '.join(s.get('listening_signals', [])) or '（数据不足）'}

### 消息样本（来自优质对话片段）

{chr(10).join(f'> "{sample}"' for sample in s.get('message_samples', [])[:5]) or '（暂无样本）'}

---

## Layer 3：情感模式

### 让你开心的行为 TOP{len(ip.get('your_happiest_triggers', []))}

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(ip.get('your_happiest_triggers', [])))}

### 最佳互动类型

{chr(10).join(f'- {t}' for t in ip.get('best_conversation_types', []))}

### 你的最佳状态时间段

{', '.join(ip.get('best_time_slots', ['暂无数据']))}

---

## Layer 4：关系行为

### 不让你开心的行为

{chr(10).join(f'- {t}' for t in ip.get('your_unhappy_triggers', [])) or '- （数据待积累）'}

### 有效的开场白特征

{chr(10).join(f'- {s_}' for s_ in ip.get('effective_starters', [])) or '- （数据待积累）'}

---

## Layer 5：偏好冲突提示

{conflict_section}

---

## 前任贡献图谱

{contrib_table}

---

## Layer 6：Correction 记录（对话中动态追加）

<!-- 每次 /ideal-chat 对话结束后自动写入触发正向情绪的新行为 -->
"""


def main():
    parser = argparse.ArgumentParser(description='跨前任聚合分析工具')
    parser.add_argument('--data-dir', default='data/exes', help='存放各前任数据的目录')
    parser.add_argument('--output-dir', default='data/ideal', help='输出目录')
    args = parser.parse_args()

    features_list = load_all_features(args.data_dir)
    if not features_list:
        print("错误：未找到任何前任特征数据，请先运行 /analyze-ex", file=sys.stderr)
        sys.exit(1)

    weights = [calc_weight(f) for f in features_list]
    total_w = sum(weights) or 1

    print(f"加载 {len(features_list)} 位前任数据，权重分布：")
    for feat, w in zip(features_list, weights):
        print(f"  {feat.get('name', feat.get('slug'))}: 权重 {w} ({w/total_w:.1%})")

    merged_personality = merge_personality(features_list, weights)
    merged_style = merge_style(features_list, weights)
    merged_interaction = merge_interaction(features_list, weights)

    # 确定版本号
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'versions').mkdir(exist_ok=True)

    persona_path = output_dir / 'persona.md'
    version = 1
    if persona_path.exists():
        # 读取当前版本号
        content = persona_path.read_text(encoding='utf-8')
        import re
        m = re.search(r'v(\d+)', content)
        if m:
            version = int(m.group(1)) + 1

    persona_content = build_persona_md(
        merged_personality, merged_style, merged_interaction,
        features_list, weights, version
    )

    # 写入
    persona_path.write_text(persona_content, encoding='utf-8')

    # 同时写入聚合数据 JSON
    agg_data = {
        'version': version,
        'sources': [f.get('slug') for f in features_list],
        'personality': merged_personality,
        'style': merged_style,
        'interaction': merged_interaction,
        'weights': {f.get('slug'): w for f, w in zip(features_list, weights)},
    }
    with open(output_dir / 'aggregated.json', 'w', encoding='utf-8') as fp:
        json.dump(agg_data, fp, ensure_ascii=False, indent=2)

    print(f"聚合完成：生成 persona.md v{version}，已写入 {persona_path}")


if __name__ == '__main__':
    main()
