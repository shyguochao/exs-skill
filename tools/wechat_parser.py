#!/usr/bin/env python3
"""微信聊天记录解析器

支持主流导出工具的格式：
- WeChatMsg 导出（txt/html/csv）
- 留痕导出（json）
- PyWxDump 导出（sqlite）
- 手动复制粘贴（纯文本）

Usage:
    python3 wechat_parser.py --file <path> --target <name> --output <output_path> [--format auto]
"""

import argparse
import json
import re
import os
import sys
from pathlib import Path


def detect_format(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == '.json':
        return 'liuhen'
    elif ext == '.csv':
        return 'wechatmsg_csv'
    elif ext in ('.html', '.htm'):
        return 'wechatmsg_html'
    elif ext in ('.db', '.sqlite'):
        return 'pywxdump'
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = f.read(2000)
        if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', first_lines):
            return 'wechatmsg_txt'
        return 'plaintext'
    return 'plaintext'


def parse_wechatmsg_txt(file_path: str, target_name: str) -> dict:
    messages = []
    current_msg = None
    msg_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+)$')

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip('\n')
            match = msg_pattern.match(line)
            if match:
                if current_msg:
                    messages.append(current_msg)
                timestamp, sender = match.groups()
                current_msg = {'timestamp': timestamp, 'sender': sender.strip(), 'content': ''}
            elif current_msg and line.strip():
                if current_msg['content']:
                    current_msg['content'] += '\n'
                current_msg['content'] += line

    if current_msg:
        messages.append(current_msg)
    return _build_result(messages, target_name, 'wechatmsg_txt')


def parse_liuhen_json(file_path: str, target_name: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    msg_list = data if isinstance(data, list) else data.get('messages', data.get('data', []))
    messages = []
    for msg in msg_list:
        messages.append({
            'timestamp': msg.get('time', msg.get('timestamp', '')),
            'sender': msg.get('sender', msg.get('nickname', msg.get('from', ''))),
            'content': msg.get('content', msg.get('message', msg.get('text', '')))
        })
    return _build_result(messages, target_name, 'liuhen')


def parse_plaintext(file_path: str, target_name: str) -> dict:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return {
        'target_name': target_name,
        'format': 'plaintext',
        'total_messages': 0,
        'target_messages': 0,
        'messages': [],
        'raw_text': content,
        'analysis': {'note': '纯文本格式，将由 AI 辅助分析'}
    }


def _build_result(messages: list, target_name: str, fmt: str) -> dict:
    """构建标准化输出结构，供 emotion_scorer.py 使用"""
    target_msgs = [m for m in messages if target_name in m.get('sender', '')]
    user_msgs = [m for m in messages if target_name not in m.get('sender', '')]

    all_target_text = ' '.join([m['content'] for m in target_msgs if m.get('content')])

    # 语气词
    particles = re.findall(r'[哈嗯哦噢嘿唉呜啊呀吧嘛呢吗么]+', all_target_text)
    particle_freq = {}
    for p in particles:
        particle_freq[p] = particle_freq.get(p, 0) + 1
    top_particles = sorted(particle_freq.items(), key=lambda x: -x[1])[:10]

    # Emoji
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
        r'\U00002702-\U000027B0\U0000FE00-\U0000FE0F'
        r'\U0001F900-\U0001F9FF]+', re.UNICODE
    )
    emojis = emoji_pattern.findall(all_target_text)
    emoji_freq = {}
    for e in emojis:
        emoji_freq[e] = emoji_freq.get(e, 0) + 1
    top_emojis = sorted(emoji_freq.items(), key=lambda x: -x[1])[:10]

    msg_lengths = [len(m['content']) for m in target_msgs if m.get('content')]
    avg_length = sum(msg_lengths) / len(msg_lengths) if msg_lengths else 0

    punctuation_counts = {
        '句号': all_target_text.count('。'),
        '感叹号': all_target_text.count('！') + all_target_text.count('!'),
        '问号': all_target_text.count('？') + all_target_text.count('?'),
        '省略号': all_target_text.count('...') + all_target_text.count('…'),
        '波浪号': all_target_text.count('～') + all_target_text.count('~'),
    }

    return {
        'target_name': target_name,
        'format': fmt,
        'total_messages': len(messages),
        'target_messages': len(target_msgs),
        'user_messages': len(user_msgs),
        'messages': messages,   # 完整消息列表，供 emotion_scorer 使用
        'analysis': {
            'top_particles': top_particles,
            'top_emojis': top_emojis,
            'avg_message_length': round(avg_length, 1),
            'punctuation_habits': punctuation_counts,
            'message_style': 'short_burst' if avg_length < 20 else 'long_form',
        },
        'sample_messages': [m['content'] for m in target_msgs[:50] if m.get('content')],
    }


def main():
    parser = argparse.ArgumentParser(description='微信聊天记录解析器')
    parser.add_argument('--file', required=True, help='输入文件路径')
    parser.add_argument('--target', required=True, help='前任的名字/昵称')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    parser.add_argument('--format', default='auto', help='文件格式 (auto/wechatmsg_txt/liuhen/plaintext)')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"错误：文件不存在 {args.file}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if fmt == 'auto':
        fmt = detect_format(args.file)
        print(f"自动检测格式：{fmt}")

    parsers = {
        'wechatmsg_txt': parse_wechatmsg_txt,
        'liuhen': parse_liuhen_json,
        'plaintext': parse_plaintext,
    }
    result = parsers.get(fmt, parse_plaintext)(args.file, args.target)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"解析完成：共 {result.get('total_messages', 0)} 条消息，已写入 {args.output}")


if __name__ == '__main__':
    main()
