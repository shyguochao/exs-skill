#!/usr/bin/env python3
"""版本管理工具

对 data/ideal/ 目录下的核心文件进行快照备份和回滚。
保留最近 10 个版本，自动清理更早的版本。

Usage:
    python3 version_manager.py --action backup --output-dir <data/ideal>
    python3 version_manager.py --action rollback --output-dir <data/ideal> --version v2
    python3 version_manager.py --action list --output-dir <data/ideal>
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

CORE_FILES = ['persona.md', 'template.md', 'aggregated.json']
MAX_VERSIONS = 10


def _versions_dir(output_dir: str) -> Path:
    return Path(output_dir) / 'versions'


def action_backup(output_dir: str) -> str:
    """备份当前核心文件"""
    out = Path(output_dir)
    versions_dir = _versions_dir(output_dir)
    versions_dir.mkdir(parents=True, exist_ok=True)

    # 确定版本号
    persona_path = out / 'persona.md'
    version_num = 1
    if persona_path.exists():
        import re
        m = re.search(r'v(\d+)', persona_path.read_text(encoding='utf-8'))
        if m:
            version_num = int(m.group(1))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    snapshot_name = f"v{version_num}_{timestamp}"
    snapshot_dir = versions_dir / snapshot_name
    snapshot_dir.mkdir(exist_ok=True)

    copied = []
    for fname in CORE_FILES:
        src = out / fname
        if src.exists():
            shutil.copy2(src, snapshot_dir / fname)
            copied.append(fname)

    # 写入快照元数据
    meta = {
        'version': f"v{version_num}",
        'timestamp': timestamp,
        'files': copied,
    }
    with open(snapshot_dir / 'snapshot_meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 清理旧版本（保留最近 MAX_VERSIONS 个）
    _cleanup_old_versions(versions_dir)

    print(f"备份完成：{snapshot_name}（包含 {', '.join(copied)}）")
    return snapshot_name


def action_rollback(output_dir: str, version: str):
    """回滚到指定版本（回滚前先备份当前版本）"""
    versions_dir = _versions_dir(output_dir)

    # 找到目标版本目录
    target_dir = None
    for d in versions_dir.iterdir():
        if d.is_dir() and d.name.startswith(version):
            target_dir = d
            break

    if target_dir is None:
        print(f"错误：未找到版本 {version}", file=sys.stderr)
        print("可用版本：")
        action_list(output_dir)
        sys.exit(1)

    # 先备份当前版本
    print("回滚前先备份当前版本...")
    action_backup(output_dir)

    # 还原文件
    out = Path(output_dir)
    restored = []
    for fname in CORE_FILES:
        src = target_dir / fname
        if src.exists():
            shutil.copy2(src, out / fname)
            restored.append(fname)

    print(f"回滚成功：已还原到 {target_dir.name}（{', '.join(restored)}）")


def action_list(output_dir: str):
    """列出所有历史版本"""
    versions_dir = _versions_dir(output_dir)
    if not versions_dir.exists():
        print("暂无历史版本")
        return

    snapshots = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True
    )

    if not snapshots:
        print("暂无历史版本")
        return

    print(f"{'版本快照':<30} {'文件列表'}")
    print('-' * 60)
    for snap in snapshots:
        meta_file = snap / 'snapshot_meta.json'
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            files_str = ', '.join(meta.get('files', []))
        else:
            files_str = '（元数据缺失）'
        print(f"{snap.name:<30} {files_str}")


def _cleanup_old_versions(versions_dir: Path):
    """保留最近 MAX_VERSIONS 个版本，清理更早的"""
    snapshots = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True
    )
    for old in snapshots[MAX_VERSIONS:]:
        shutil.rmtree(old)
        print(f"已清理旧版本：{old.name}")


def main():
    parser = argparse.ArgumentParser(description='版本管理工具')
    parser.add_argument('--action', required=True, choices=['backup', 'rollback', 'list'])
    parser.add_argument('--output-dir', default='data/ideal', help='ideal 目录路径')
    parser.add_argument('--version', default='', help='回滚目标版本（如 v2）')
    args = parser.parse_args()

    if args.action == 'backup':
        action_backup(args.output_dir)
    elif args.action == 'rollback':
        if not args.version:
            print("错误：--action rollback 需要提供 --version", file=sys.stderr)
            sys.exit(1)
        action_rollback(args.output_dir, args.version)
    elif args.action == 'list':
        action_list(args.output_dir)


if __name__ == '__main__':
    main()
