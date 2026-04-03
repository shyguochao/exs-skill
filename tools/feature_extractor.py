#!/usr/bin/env python3
"""特征提取工具

从 emotion_scorer 输出的优质对话片段中，提取前任的说话风格特征和性格维度评分，
生成标准化的 features.json 供 ideal_builder 使用。

Usage:
    python3 feature_extractor.py --analysis <raw_analysis.json> --parsed <parsed.json>
                                  --slug <name> --output <features.json>
"""

import argparse
import json
import os
import re
import sys
from collections import Counter


# ── 说话风格信号词 ────────────────────────────────────────────

# 幽默感信号
HUMOR_SIGNALS = re.compile(r'哈哈|笑死|绷不住|离谱|抽象|hhh|😂|🤣|笑|玩笑|开玩笑|逗你')
# 共情表达
EMPATHY_SIGNALS = ['原来如此', '听起来', '感觉你', '辛苦了', '能理解', '我懂', '我知道你', '抱抱', '没事的']
# 主动关心
CARE_SIGNALS = ['你今天', '最近怎么样', '吃了吗', '睡了吗', '还好吗', '怎么了', '上次你说']
# 倾听信号
LISTENING_SIGNALS = ['继续说', '然后呢', '真的假的', '详细说', '后来呢', '嗯嗯', '说来听听']
# 开放式提问信号
OPEN_QUESTION = re.compile(r'你觉得|你怎么看|如果是你|你会怎么|为什么|你喜欢')
# 具体夸奖信号
SPECIFIC_PRAISE = re.compile(r'你[真好很]厉害|你这个[想法做法]|佩服你|你[真好]棒')


def extract_style_features(quality_segments: list, target_name: str) -> dict:
    """从优质对话片段提取说话风格特征"""
    target_texts = []
    all_ex_messages = []

    for seg in quality_segments:
        for msg in seg.get('messages', []):
            if target_name in msg.get('sender', '') and msg.get('content'):
                content = msg['content']
                target_texts.append(content)
                all_ex_messages.append(content)

    all_text = ' '.join(target_texts)
    total = len(target_texts) or 1

    # 幽默感
    humor_count = len(HUMOR_SIGNALS.findall(all_text))
    humor_freq = 'high' if humor_count / total > 0.3 else ('medium' if humor_count / total > 0.1 else 'low')

    # 话题引导（开放式提问频率）
    open_q_count = len(OPEN_QUESTION.findall(all_text))
    topic_depth = 'high' if open_q_count / total > 0.2 else ('medium' if open_q_count / total > 0.05 else 'low')

    # 共情表达
    empathy_found = [s for s in EMPATHY_SIGNALS if s in all_text]
    empathy_count = sum(all_text.count(s) for s in EMPATHY_SIGNALS)

    # 关心细节
    care_found = [s for s in CARE_SIGNALS if s in all_text]

    # 倾听信号
    listen_found = [s for s in LISTENING_SIGNALS if s in all_text]

    # 消息长度统计
    lengths = [len(t) for t in target_texts]
    avg_len = round(sum(lengths) / len(lengths), 1) if lengths else 0
    reply_style = '短句连发型' if avg_len < 20 else ('中等长度' if avg_len < 60 else '长段落型')

    # 语气词
    particles = re.findall(r'[哈嗯哦噢嘿唉呜啊呀吧嘛呢吗么]{2,}', all_text)
    top_particles = [w for w, _ in Counter(particles).most_common(5)]

    # Emoji
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]+', re.UNICODE
    )
    emojis = emoji_pattern.findall(all_text)
    top_emojis = [e for e, _ in Counter(emojis).most_common(5)]

    # 消息样本（取最具代表性的5条，长度在30-100字之间）
    samples = [t for t in target_texts if 30 <= len(t) <= 100][:5]

    return {
        'humor': {
            'frequency': humor_freq,
            'count': humor_count,
            'pattern': '幽默感强，善用网络梗和自嘲' if humor_freq == 'high' else '偶尔幽默',
        },
        'topic_leading': {
            'depth': topic_depth,
            'open_question_count': open_q_count,
            'style': '善用开放式提问引导深入' if topic_depth == 'high' else '话题引导一般',
        },
        'reply_rhythm': {
            'avg_length': avg_len,
            'style': reply_style,
            'continuity': '善于接话' if len(listen_found) >= 2 else '一般',
        },
        'empathy_expressions': empathy_found[:8],
        'empathy_score_raw': empathy_count,
        'care_expressions': care_found[:6],
        'listening_signals': listen_found[:6],
        'top_particles': top_particles,
        'top_emojis': top_emojis,
        'message_samples': samples,
        'specific_praise_count': len(SPECIFIC_PRAISE.findall(all_text)),
    }


def score_personality(quality_segments: list, raw_analysis: dict, target_name: str) -> dict:
    """评估性格维度（1-10分）"""
    total_segs = raw_analysis.get('total_segments', 1) or 1
    quality_count = raw_analysis.get('quality_segments', 0)
    quality_ratio = raw_analysis.get('quality_ratio', 0)

    # 主动性：看对方是否主动发起话题（片段中第一条是否是对方）
    initiative_count = 0
    empathy_total = 0
    humor_total = 0
    care_total = 0
    listen_total = 0

    for seg in quality_segments:
        msgs = seg.get('messages', [])
        if msgs and target_name in msgs[0].get('sender', ''):
            initiative_count += 1
        ex_text = ' '.join(m.get('content', '') for m in msgs if target_name in m.get('sender', ''))
        empathy_total += sum(ex_text.count(s) for s in EMPATHY_SIGNALS)
        humor_total += len(HUMOR_SIGNALS.findall(ex_text))
        care_total += sum(ex_text.count(s) for s in CARE_SIGNALS)
        listen_total += sum(ex_text.count(s) for s in LISTENING_SIGNALS)

    seg_count = len(quality_segments) or 1

    def norm(val, base, max_score=10):
        return min(max_score, round((val / base) * 10, 1))

    initiative_score = norm(initiative_count, seg_count * 0.6)
    empathy_score = norm(empathy_total, seg_count * 3)
    humor_score = norm(humor_total, seg_count * 2)
    care_score = norm(care_total, seg_count * 1.5)

    # 情绪稳定性：优质片段占比越高，稳定性越高
    stability_score = round(min(10, quality_ratio * 12), 1)

    # 耐心度：倾听信号密度
    patience_score = norm(listen_total, seg_count * 2)

    # 话题深度
    open_q_total = 0
    for seg in quality_segments:
        ex_text = ' '.join(m.get('content', '') for m in seg.get('messages', [])
                           if target_name in m.get('sender', ''))
        open_q_total += len(OPEN_QUESTION.findall(ex_text))
    depth_score = norm(open_q_total, seg_count * 1.5)

    # 综合化学反应评分
    chemistry = round(
        initiative_score * 0.15 + empathy_score * 0.20 + humor_score * 0.15 +
        care_score * 0.15 + stability_score * 0.15 + patience_score * 0.10 + depth_score * 0.10,
        2
    )

    return {
        'initiative_score': initiative_score,
        'emotional_stability_score': stability_score,
        'empathy_score': empathy_score,
        'humor_score': humor_score,
        'care_detail_score': care_score,
        'patience_score': patience_score,
        'topic_depth_score': depth_score,
        'chemistry_score': chemistry,
    }


def extract_interaction_patterns(quality_segments: list, target_name: str,
                                  raw_analysis: dict) -> dict:
    """提取互动模式：哪类话题让用户最开心，哪些行为触发正向情绪"""
    # 从触发消息（trigger_message）归类话题
    trigger_msgs = [seg.get('trigger_message', '') for seg in quality_segments if seg.get('trigger_message')]

    # 话题分类关键词
    topic_keywords = {
        '分享日常趣事': re.compile(r'今天|刚才|发生|跟你说|听说'),
        '讨论未来计划': re.compile(r'以后|将来|下次|计划|打算|想去|要不要'),
        '互相吐槽': re.compile(r'哈哈|离谱|无语|太过分|抽象|绷不住'),
        '深夜聊心里话': re.compile(r'其实|说实话|一直|从来|有时候|感觉自己'),
        '共同话题探讨': re.compile(r'你觉得|你喜欢|推荐|看过|玩过|听过'),
        '关心问候': re.compile(r'怎么了|还好吗|累不累|吃了吗|最近'),
    }

    best_topics = []
    for topic, pattern in topic_keywords.items():
        count = sum(1 for t in trigger_msgs if pattern.search(t))
        if count > 0:
            best_topics.append((topic, count))
    best_topics.sort(key=lambda x: -x[1])

    # 从 peak_message（情绪峰值时用户回复）推断触发行为
    peak_msgs = [seg.get('trigger_message', '') for seg in quality_segments if seg.get('peak_message')]

    # 触发用户开心的行为：从触发消息特征归纳
    happiest_triggers = []
    trigger_all = ' '.join(trigger_msgs)
    if HUMOR_SIGNALS.search(trigger_all):
        happiest_triggers.append('用幽默感引发笑点')
    if any(s in trigger_all for s in CARE_SIGNALS):
        happiest_triggers.append('主动关心你的状态')
    if OPEN_QUESTION.search(trigger_all):
        happiest_triggers.append('用问题引导你深入分享')
    if any(s in trigger_all for s in ['上次你说', '之前你提到', '你跟我说过']):
        happiest_triggers.append('记住你说过的小事并提起')
    if any(s in trigger_all for s in EMPATHY_SIGNALS):
        happiest_triggers.append('在你难过时给出共情回应')

    unhappy_triggers = []
    # 从非优质片段的第一条对方消息推断
    for seg in [s for s in quality_segments if not s.get('is_quality', True)]:
        msgs = seg.get('messages', [])
        for msg in msgs[:2]:
            if target_name in msg.get('sender', '') and msg.get('content'):
                c = msg['content']
                if len(c) <= 3:
                    unhappy_triggers.append('只回复一两个字，不接话')
                    break

    return {
        'best_conversation_types': [t for t, _ in best_topics[:5]],
        'your_happiest_triggers': list(dict.fromkeys(happiest_triggers))[:6],
        'your_unhappy_triggers': list(dict.fromkeys(unhappy_triggers))[:4],
        'best_time_slots': raw_analysis.get('best_time_slots', []),
        'effective_starters': raw_analysis.get('conversation_starters', {}).get('effective_starters', []),
    }


def main():
    parser = argparse.ArgumentParser(description='特征提取工具')
    parser.add_argument('--analysis', required=True, help='emotion_scorer 输出的 raw_analysis.json')
    parser.add_argument('--parsed', required=True, help='wechat_parser/qq_parser 输出的原始 JSON')
    parser.add_argument('--slug', required=True, help='前任的 slug（代号）')
    parser.add_argument('--name', default='', help='前任的姓名/昵称')
    parser.add_argument('--output', required=True, help='输出 features.json 路径')
    args = parser.parse_args()

    for path in [args.analysis, args.parsed]:
        if not os.path.exists(path):
            print(f"错误：文件不存在 {path}", file=sys.stderr)
            sys.exit(1)

    with open(args.analysis, 'r', encoding='utf-8') as f:
        raw_analysis = json.load(f)
    with open(args.parsed, 'r', encoding='utf-8') as f:
        parsed = json.load(f)

    target_name = parsed.get('target_name', args.slug)
    quality_segments = [s for s in raw_analysis.get('segments', []) if s.get('is_quality')]

    if not quality_segments:
        print("警告：未找到优质对话片段，特征提取结果可能不准确", file=sys.stderr)

    style = extract_style_features(quality_segments, target_name)
    personality = score_personality(quality_segments, raw_analysis, target_name)
    interaction = extract_interaction_patterns(quality_segments, target_name, raw_analysis)

    result = {
        'slug': args.slug,
        'name': args.name or target_name,
        'quality_segments_count': len(quality_segments),
        'quality_ratio': raw_analysis.get('quality_ratio', 0),
        'style_features': style,
        'personality_features': personality,
        'interaction_patterns': interaction,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"特征提取完成：化学反应评分 {personality['chemistry_score']}，已写入 {args.output}")


if __name__ == '__main__':
    main()
