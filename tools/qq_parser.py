#!/usr/bin/env python3
"""QQ 聊天记录解析器

支持格式：
- QQ 消息管理器导出的 txt 格式
- QQ 消息管理器导出的 mht 格式

Usage:
    python3 qq_parser.py --file <path> --target <name> --output <output_path>
"""

import argparse
import json
import re
import os
import sys
from pathlib import Path


def parse_qq_txt(file_path: str, target_name: str) -> dict:
    """解析 QQ 导出的 txt 格式

    典型格式：
    2024-01-15 20:30:45 张三(123456)
    今天好累
    """
    messages = []
    current_msg = None
    msg_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+?)(?:\((\d+)\))?\s*$')

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip('\n')
            match = msg_pattern.match(line)
            if match:
                if current_msg:
                    messages.append(current_msg)
                timestamp, sender, _ = match.groups()
                current_msg = {'timestamp': timestamp, 'sender': sender.strip(), 'content': ''}
            elif current_msg and line.strip() and not line.startswith('==='):
                if current_msg['content']:
                    current_msg['content'] += '\n'
                current_msg['content'] += line

    if current_msg:
        messages.append(current_msg)
    return _build_result(messages, target_name, 'qq_txt')


def parse_qq_mht(file_path: str, target_name: str) -> dict:
    """解析 QQ 导出的 mht 格式"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    clean_text = re.sub(r'<[^>]+>', '\n', content)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    return {
        'target_name': target_name,
        'format': 'qq_mht',
        'total_messages': 0,
        'target_messages': 0,
        'user_messages': 0,
        'messages': [],
        'raw_text': clean_text[:20000],
        'analysis': {'note': 'MHT 格式，已提取纯文本，将由 AI 辅助分析'}
    }


def _build_result(messages: list, target_name: str, fmt: str) -> dict:
    target_msgs = [m for m in messages if target_name in m.get('sender', '')]
    user_msgs = [m for m in messages if target_name not in m.get('sender', '')]
    all_target_text = ' '.join([m['content'] for m in target_msgs if m.get('content')])

    particles = re.findall(r'[哈嗯哦噢嘿唉呜啊呀吧嘛呢吗么]+', all_target_text)
    particle_freq = {}
    for p in particles:
        particle_freq[p] = particle_freq.get(p, 0) + 1
    top_particles = sorted(particle_freq.items(), key=lambda x: -x[1])[:10]

    msg_lengths = [len(m['content']) for m in target_msgs if m.get('content')]
    avg_length = sum(msg_lengths) / len(msg_lengths) if msg_lengths else 0

    return {
        'target_name': target_name,
        'format': fmt,
        'total_messages': len(messages),
        'target_messages': len(target_msgs),
        'user_messages': len(user_msgs),
        'messages': messages,
        'analysis': {
            'top_particles': top_particles,
            'avg_message_length': round(avg_length, 1),
            'message_style': 'short_burst' if avg_length < 20 else 'long_form',
        },
        'sample_messages': [m['content'] for m in target_msgs[:50] if m.get('content')],
    }


def main():
    parser = argparse.ArgumentParser(description='QQ 聊天记录解析器')
    parser.add_argument('--file', required=True, help='输入文件路径')
    parser.add_argument('--target', required=True, help='前任的名字/昵称')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"错误：文件不存在 {args.file}", file=sys.stderr)
        sys.exit(1)

    ext = Path(args.file).suffix.lower()
    result = parse_qq_mht(args.file, args.target) if ext in ('.mht', '.mhtml') else parse_qq_txt(args.file, args.target)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"解析完成：共 {result.get('total_messages', 0)} 条消息，已写入 {args.output}")


if __name__ == '__main__':
    main()
