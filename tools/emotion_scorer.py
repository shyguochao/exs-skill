#!/usr/bin/env python3
"""情绪评分核心引擎

读取 wechat_parser / qq_parser 输出的 JSON，对用户回复逐条情绪打分，
按时间分段，识别优质对话片段（用户情绪呈上升趋势的片段）。

Usage:
    python3 emotion_scorer.py --input <parsed.json> --user <你的名字> --output <raw_analysis.json>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Optional

# ── 情绪信号权重 ──────────────────────────────────────────────
EMOTION_WEIGHTS = {
    'happy_emoji':        3.0,
    'positive_particles': 1.5,
    'exclamation':        1.0,
    'question':           1.2,   # 主动追问 = 参与度高
    'reply_length_up':    2.0,   # 回复变长 = 投入度上升
    'reply_speed_up':     1.8,
    'initiative':         2.5,   # 用户主动发起新话题
    'negative_emoji':    -3.0,
    'negative_particles':-2.0,
    'reply_length_down': -1.5,
}

# ── 正负向信号词库 ────────────────────────────────────────────
HAPPY_EMOJI_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F970\U0001F973\U0001F929\U0001F60D'
    r'\U00002764\U0001F495-\U0001F49F]+', re.UNICODE
)
NEGATIVE_EMOJI_PATTERN = re.compile(
    r'[\U0001F620-\U0001F625\U0001F62D\U0001F641\U0001F614\U0001F615'
    r'\U0001F616\U0001F62B\U0001F629\U0001F92F]+', re.UNICODE
)
POSITIVE_PARTICLES = re.compile(r'哈{2,}|嗯{2,}|好呀|好啊|真的吗|然后呢|继续说|详细说|太[好棒赞爽]了')
NEGATIVE_PARTICLES = re.compile(r'^哦$|^嗯$|^随便$|^都行$|^无所谓$')

# ── 优质对话判定规则 ──────────────────────────────────────────
QUALITY_RULES = {
    'min_avg_score':       6.0,
    'trend':               'ascending',
    'min_messages':        20,
    'min_peak_score':      7.5,
}

# 超过此时间间隔（秒）则切分为新片段
SEGMENT_GAP_SECONDS = 7200  # 2 小时


def _parse_ts(ts_str: str) -> Optional[datetime]:
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def score_message(content: str, prev_length: int, prev_ts: Optional[datetime],
                  curr_ts: Optional[datetime], prev_score: float) -> float:
    """对单条用户消息打分"""
    score = 0.0
    if not content:
        return score

    # 正向 emoji
    happy = HAPPY_EMOJI_PATTERN.findall(content)
    score += len(happy) * EMOTION_WEIGHTS['happy_emoji']

    # 负向 emoji
    negative = NEGATIVE_EMOJI_PATTERN.findall(content)
    score += len(negative) * EMOTION_WEIGHTS['negative_emoji']

    # 正向语气词
    pos = POSITIVE_PARTICLES.findall(content)
    score += len(pos) * EMOTION_WEIGHTS['positive_particles']

    # 负向语气词（整条消息就是这几个字）
    stripped = content.strip()
    if NEGATIVE_PARTICLES.match(stripped) and len(stripped) <= 4:
        score += EMOTION_WEIGHTS['negative_particles']

    # 感叹号
    excl = content.count('！') + content.count('!')
    score += min(excl, 3) * EMOTION_WEIGHTS['exclamation']

    # 主动追问（问号 + 消息较短）
    q_count = content.count('？') + content.count('?')
    if q_count > 0 and len(content) < 30:
        score += EMOTION_WEIGHTS['question']

    # 回复长度变化
    curr_length = len(content)
    if prev_length > 0:
        if curr_length > prev_length * 1.3:
            score += EMOTION_WEIGHTS['reply_length_up']
        elif curr_length < prev_length * 0.5:
            score += EMOTION_WEIGHTS['reply_length_down']

    # 回复速度（需要时间戳）
    if prev_ts and curr_ts:
        gap = (curr_ts - prev_ts).total_seconds()
        if 0 < gap < 60:
            score += EMOTION_WEIGHTS['reply_speed_up']

    # 归一化到 0-10
    score = max(0.0, min(10.0, score + 5.0))
    return round(score, 2)


def segment_conversation(messages: list) -> list:
    """按时间间隔将消息列表切分为对话片段"""
    if not messages:
        return []

    segments = []
    current = []

    for msg in messages:
        if not current:
            current.append(msg)
            continue
        prev_ts = _parse_ts(current[-1].get('timestamp', ''))
        curr_ts = _parse_ts(msg.get('timestamp', ''))
        if prev_ts and curr_ts:
            gap = (curr_ts - prev_ts).total_seconds()
            if gap > SEGMENT_GAP_SECONDS:
                segments.append(current)
                current = [msg]
                continue
        current.append(msg)

    if current:
        segments.append(current)
    return segments


def calc_trend(scores: list) -> str:
    """计算情绪趋势"""
    if len(scores) < 3:
        return 'stable'
    # 线性回归斜率
    n = len(scores)
    x_mean = (n - 1) / 2
    y_mean = sum(scores) / n
    num = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 'stable'
    slope = num / den
    if slope > 0.15:
        return 'ascending'
    elif slope < -0.15:
        return 'descending'
    return 'stable'


def is_quality_segment(scores: list, trend: str) -> bool:
    if len(scores) < QUALITY_RULES['min_messages']:
        return False
    if trend != QUALITY_RULES['trend']:
        return False
    avg = sum(scores) / len(scores)
    if avg < QUALITY_RULES['min_avg_score']:
        return False
    if max(scores) < QUALITY_RULES['min_peak_score']:
        return False
    return True


def analyze_time_slots(quality_segments: list) -> dict:
    """统计优质对话的时间段分布"""
    hour_counts = {}
    weekday_counts = {}
    for seg in quality_segments:
        for msg in seg.get('messages', []):
            ts = _parse_ts(msg.get('timestamp', ''))
            if ts:
                h = ts.hour
                hour_counts[h] = hour_counts.get(h, 0) + 1
                wd = ts.strftime('%A')
                weekday_counts[wd] = weekday_counts.get(wd, 0) + 1

    def hour_label(h):
        if 6 <= h < 12:
            return '上午'
        elif 12 <= h < 18:
            return '下午'
        elif 18 <= h < 23:
            return '晚上'
        return '深夜'

    # 找出最高频的时间段
    if hour_counts:
        top_hours = sorted(hour_counts.items(), key=lambda x: -x[1])[:3]
        best_slots = list({hour_label(h) for h, _ in top_hours})
    else:
        best_slots = []

    top_weekdays = sorted(weekday_counts.items(), key=lambda x: -x[1])[:2]
    return {'best_time_slots': best_slots, 'top_weekdays': [d for d, _ in top_weekdays]}


def analyze_starters(quality_segments: list, target_name: str) -> dict:
    """分析对方哪类开场白触发了优质对话"""
    effective = []
    for seg in quality_segments:
        msgs = seg.get('messages', [])
        # 找片段第一条对方消息
        for msg in msgs[:3]:
            if target_name in msg.get('sender', '') and msg.get('content'):
                content = msg['content'][:50]
                if content not in effective:
                    effective.append(content)
                break
    return {'effective_starters': effective[:5]}


def score_all(parsed: dict, user_name: str) -> dict:
    """主流程：对全部消息评分并识别优质片段"""
    messages = parsed.get('messages', [])
    target_name = parsed.get('target_name', '')

    raw_segments = segment_conversation(messages)
    scored_segments = []
    quality_segments = []

    for idx, seg_msgs in enumerate(raw_segments):
        user_msgs = [m for m in seg_msgs if user_name in m.get('sender', '')]
        if len(user_msgs) < 5:
            continue

        scores = []
        prev_length = 0
        prev_ts = None
        prev_score = 5.0

        for msg in user_msgs:
            curr_ts = _parse_ts(msg.get('timestamp', ''))
            s = score_message(msg.get('content', ''), prev_length, prev_ts, curr_ts, prev_score)
            scores.append(s)
            prev_length = len(msg.get('content', ''))
            prev_ts = curr_ts
            prev_score = s

        if not scores:
            continue

        trend = calc_trend(scores)
        avg_score = round(sum(scores) / len(scores), 2)
        peak_score = round(max(scores), 2)
        quality = is_quality_segment(scores, trend)

        # 找触发上升的第一条对方消息
        trigger_msg = ''
        peak_msg = ''
        for m in seg_msgs:
            if target_name in m.get('sender', '') and m.get('content'):
                trigger_msg = m['content'][:100]
                break
        if scores:
            peak_idx = scores.index(max(scores))
            user_msg_at_peak = user_msgs[peak_idx] if peak_idx < len(user_msgs) else None
            if user_msg_at_peak:
                peak_msg = user_msg_at_peak.get('content', '')[:100]

        # 用户信号统计
        all_user_text = ' '.join([m.get('content', '') for m in user_msgs])
        happy_emojis = HAPPY_EMOJI_PATTERN.findall(all_user_text)
        pos_particles = POSITIVE_PARTICLES.findall(all_user_text)
        excl_count = all_user_text.count('！') + all_user_text.count('!')
        q_count = all_user_text.count('？') + all_user_text.count('?')

        seg_record = {
            'segment_id': f'seg_{idx:03d}',
            'message_count': len(seg_msgs),
            'user_message_count': len(user_msgs),
            'emotion_trend': trend,
            'avg_score': avg_score,
            'peak_score': peak_score,
            'is_quality': quality,
            'trigger_message': trigger_msg,
            'peak_message': peak_msg,
            'user_signals': {
                'happy_emoji_count': len(happy_emojis),
                'happy_emojis': list(set(happy_emojis))[:5],
                'positive_particles_count': len(pos_particles),
                'exclamation_count': excl_count,
                'question_count': q_count,
                'avg_reply_length': round(sum(len(m.get('content', '')) for m in user_msgs) / len(user_msgs), 1),
            },
            'conversation_sample': [
                {'sender': m.get('sender', ''), 'text': m.get('content', '')[:80]}
                for m in seg_msgs[:6]
            ],
            'messages': seg_msgs,
        }
        scored_segments.append(seg_record)
        if quality:
            quality_segments.append(seg_record)

    quality_ratio = len(quality_segments) / len(scored_segments) if scored_segments else 0.0
    time_info = analyze_time_slots(quality_segments)
    starters = analyze_starters(quality_segments, target_name)

    return {
        'ex_slug': parsed.get('target_name', ''),
        'total_messages': parsed.get('total_messages', 0),
        'total_segments': len(scored_segments),
        'quality_segments': len(quality_segments),
        'quality_ratio': round(quality_ratio, 3),
        'best_time_slots': time_info['best_time_slots'],
        'top_weekdays': time_info['top_weekdays'],
        'conversation_starters': starters,
        'segments': scored_segments,
    }


def main():
    parser = argparse.ArgumentParser(description='情绪评分引擎')
    parser.add_argument('--input', required=True, help='wechat_parser/qq_parser 输出的 JSON 文件')
    parser.add_argument('--user', required=True, help='你的名字/昵称（区分用户消息）')
    parser.add_argument('--output', required=True, help='输出 raw_analysis.json 路径')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误：文件不存在 {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        parsed = json.load(f)

    result = score_all(parsed, args.user)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"评分完成：{result['total_segments']} 个片段，"
          f"其中 {result['quality_segments']} 个优质片段（占比 {result['quality_ratio']:.1%}），"
          f"已写入 {args.output}")


if __name__ == '__main__':
    main()
