#!/usr/bin/env python3
"""Skill 文件管理工具

管理 data/ideal/ 目录下的 Skill 文件，支持初始化、组合生成和列表查看。

Usage:
    python3 skill_writer.py --action init --slug <name>
    python3 skill_writer.py --action combine --output-dir <data/ideal>
    python3 skill_writer.py --action list --data-dir <data/exes>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def action_init(slug: str, data_dir: str):
    """初始化前任数据目录"""
    slug_dir = Path(data_dir) / slug
    for sub in ['memories/chats', 'memories/photos']:
        (slug_dir / sub).mkdir(parents=True, exist_ok=True)
    print(f"已初始化目录：{slug_dir}")


def action_combine(output_dir: str):
    """读取 persona.md 生成可运行的 ideal/SKILL.md"""
    out = Path(output_dir)
    persona_path = out / 'persona.md'
    if not persona_path.exists():
        print("错误：persona.md 不存在，请先运行 /analyze-ex", file=sys.stderr)
        sys.exit(1)

    persona_content = persona_path.read_text(encoding='utf-8')

    # 提取版本号
    version = 'v1'
    m = re.search(r'v(\d+)', persona_content)
    if m:
        version = f"v{m.group(1)}"

    skill_content = f"""---
name: ideal-partner
description: 基于真实聊天数据提炼的理想对象 AI，支持对话、模版导出和恋爱顾问三大功能
version: {version}
allowed-tools: Read, Write, Edit, Bash
---

{persona_content}
"""
    skill_path = out / 'SKILL.md'
    skill_path.write_text(skill_content, encoding='utf-8')
    print(f"SKILL.md 已生成：{skill_path}（{version}）")


def action_list(data_dir: str):
    """列出所有已录入的前任"""
    exes_dir = Path(data_dir)
    if not exes_dir.exists():
        print("暂无前任数据，请先运行 /analyze-ex")
        return

    rows = []
    for slug_dir in sorted(exes_dir.iterdir()):
        feat_file = slug_dir / 'features.json'
        if feat_file.exists():
            with open(feat_file, 'r', encoding='utf-8') as f:
                feat = json.load(f)
            name = feat.get('name', slug_dir.name)
            chem = feat.get('personality_features', {}).get('chemistry_score', 'N/A')
            qr = feat.get('quality_ratio', 0)
            qc = feat.get('quality_segments_count', 0)
            rows.append((name, slug_dir.name, chem, f"{qr:.1%}", qc))

    if not rows:
        print("暂无前任数据，请先运行 /analyze-ex")
        return

    print(f"{'姓名':<10} {'代号':<12} {'化学反应评分':<12} {'优质对话占比':<12} {'优质片段数'}")
    print('-' * 60)
    for name, slug, chem, qr, qc in rows:
        print(f"{name:<10} {slug:<12} {str(chem):<12} {qr:<12} {qc}")


def main():
    parser = argparse.ArgumentParser(description='Skill 文件管理工具')
    parser.add_argument('--action', required=True, choices=['init', 'combine', 'list'])
    parser.add_argument('--slug', default='', help='前任代号（init 时使用）')
    parser.add_argument('--data-dir', default='data/exes', help='前任数据目录')
    parser.add_argument('--output-dir', default='data/ideal', help='ideal Skill 输出目录')
    args = parser.parse_args()

    if args.action == 'init':
        if not args.slug:
            print("错误：--action init 需要提供 --slug", file=sys.stderr)
            sys.exit(1)
        action_init(args.slug, args.data_dir)
    elif args.action == 'combine':
        action_combine(args.output_dir)
    elif args.action == 'list':
        action_list(args.data_dir)


if __name__ == '__main__':
    main()
