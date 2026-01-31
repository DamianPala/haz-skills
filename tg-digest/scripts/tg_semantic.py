#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
TG Digest - Chunk Splitter for Semantic Analysis

Splits large exports into smaller chunks for parallel subagent analysis.
No external dependencies - pure Python.

Usage:
  # Split export into chunks of 500 messages each
  uv run tg_semantic.py split export.json --size 500

  # Split with custom output directory
  uv run tg_semantic.py split export.json --size 500 --output /tmp/chunks

Output:
  Creates chunk_001.json, chunk_002.json, etc. in output directory.
  Each chunk contains messages + metadata for subagent consumption.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


# Default chunk size - balance between context and parallelism
DEFAULT_CHUNK_SIZE = 500


def load_export(export_path: Path) -> dict:
    """Load exported messages from JSON file."""
    with open(export_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def split_export(
    export_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    output_dir: Path | None = None,
) -> list[Path]:
    """
    Split export into chunk files for parallel processing.

    Returns list of created chunk file paths.
    """
    print(f"Loading export: {export_path}")
    data = load_export(export_path)
    messages = data.get('messages', [])
    channel = data.get('channel', {})
    export_info = data.get('export_info', {})

    if not messages:
        print("Error: No messages in export")
        sys.exit(1)

    total = len(messages)
    print(f"Total messages: {total}")

    # Determine output directory
    if output_dir is None:
        output_dir = export_path.parent / f"{export_path.stem}_chunks"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate number of chunks
    num_chunks = (total + chunk_size - 1) // chunk_size
    print(f"Splitting into {num_chunks} chunks of ~{chunk_size} messages")

    chunk_paths = []
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total)
        chunk_msgs = messages[start_idx:end_idx]

        # Build chunk metadata
        chunk_data = {
            'chunk_info': {
                'chunk_number': i + 1,
                'total_chunks': num_chunks,
                'start_idx': start_idx,
                'end_idx': end_idx,
                'message_count': len(chunk_msgs),
                'start_date': chunk_msgs[0].get('date', '')[:10] if chunk_msgs else '',
                'end_date': chunk_msgs[-1].get('date', '')[:10] if chunk_msgs else '',
            },
            'channel': channel,
            'export_info': export_info,
            'messages': chunk_msgs,
        }

        # Write chunk file
        chunk_path = output_dir / f"chunk_{i+1:03d}.json"
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)
        chunk_paths.append(chunk_path)

        print(f"  Created: {chunk_path.name} ({len(chunk_msgs)} msgs, {chunk_msgs[0].get('date', '')[:10]} → {chunk_msgs[-1].get('date', '')[:10]})")

    # Write manifest
    manifest = {
        'source': str(export_path),
        'channel': channel,
        'total_messages': total,
        'chunk_size': chunk_size,
        'num_chunks': num_chunks,
        'created_at': datetime.now().isoformat(),
        'chunks': [
            {
                'path': str(p),
                'filename': p.name,
            }
            for p in chunk_paths
        ],
    }
    manifest_path = output_dir / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nManifest: {manifest_path}")

    print(f"\n✅ Created {num_chunks} chunks in: {output_dir}")
    return chunk_paths


def main():
    parser = argparse.ArgumentParser(
        description="Split Telegram exports into chunks for parallel analysis"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Split command
    split_parser = subparsers.add_parser('split', help='Split export into chunks')
    split_parser.add_argument('export', type=Path, help='Export JSON file')
    split_parser.add_argument('--size', type=int, default=DEFAULT_CHUNK_SIZE,
                              help=f'Messages per chunk (default: {DEFAULT_CHUNK_SIZE})')
    split_parser.add_argument('--output', '-o', type=Path, default=None,
                              help='Output directory (default: {export}_chunks/)')

    args = parser.parse_args()

    if args.command == 'split':
        split_export(args.export, args.size, args.output)


if __name__ == "__main__":
    main()
