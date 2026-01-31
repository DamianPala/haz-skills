#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["telethon"]
# ///
"""
TG Digest - Telegram Channel Export Tool

Exports messages from a Telegram channel for a given date range.
Uses Telethon library with user's own API credentials.

Environment variables required:
  TG_API_ID     - Telegram API ID (from my.telegram.org)
  TG_API_HASH   - Telegram API Hash (from my.telegram.org)

Usage:
  uv run tg_export.py --channel @channelname --start-date 2025-01-01 --end-date 2025-01-31 --output export.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    SessionPasswordNeededError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
    InviteHashInvalidError,
    InviteHashExpiredError,
)
from telethon.tl.types import Channel, Chat, User
from telethon.tl.functions.messages import CheckChatInviteRequest


SESSION_PATH = Path.home() / ".tg-digest-session"


def get_credentials():
    """Get API credentials from environment variables."""
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")

    if not api_id or not api_hash:
        print("Error: Missing credentials in environment variables.")
        print()
        print("Set variables:")
        print('  export TG_API_ID="your_api_id"')
        print('  export TG_API_HASH="your_api_hash"')
        print()
        print("Get credentials at: https://my.telegram.org")
        sys.exit(1)

    return int(api_id), api_hash


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"Error: Invalid date format: {date_str}")
        print("  Use format: YYYY-MM-DD (e.g., 2025-01-01)")
        sys.exit(1)


def parse_channel_input(channel: str) -> tuple[str, bool]:
    """Parse channel input to identifier.

    Returns (identifier, is_invite_link)
    """
    channel = channel.strip().rstrip("/")

    # Check if it's an invite link (contains + or joinchat)
    if "t.me/+" in channel:
        hash_part = channel.split("+")[-1]
        return hash_part, True
    elif "t.me/joinchat/" in channel:
        hash_part = channel.split("joinchat/")[-1]
        return hash_part, True

    # Regular channel - normalize
    if channel.startswith("https://t.me/"):
        channel = channel[13:]
    elif channel.startswith("t.me/"):
        channel = channel[5:]
    elif channel.startswith("@"):
        channel = channel[1:]

    return channel, False


async def export_channel(
    channel: str,
    start_date: datetime,
    end_date: datetime,
    output_path: str,
) -> dict:
    """Export messages from channel within date range."""

    api_id, api_hash = get_credentials()
    channel_input = channel  # Save original input for export metadata

    async with TelegramClient(str(SESSION_PATH), api_id, api_hash) as client:
        # Check if we need to authenticate
        if not await client.is_user_authorized():
            print("First-time authentication required.")
            phone = input("Phone number (with country code, e.g., +1...): ").strip()
            await client.send_code_request(phone)

            code = input("Code from SMS/Telegram: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("2FA password: ").strip()
                await client.sign_in(password=password)

            print("Authentication successful!")

        # Parse channel input
        channel_id, is_invite = parse_channel_input(channel)

        if is_invite:
            print("Looking up channel via invite link...")
            try:
                invite_info = await client(CheckChatInviteRequest(channel_id))
                if hasattr(invite_info, 'chat'):
                    entity = invite_info.chat
                    print(f"Found: {entity.title}")
                else:
                    # Already a member - search in dialogs
                    print("Searching in dialogs...")
                    entity = None
                    async for dialog in client.iter_dialogs():
                        if hasattr(dialog.entity, 'title'):
                            entity = dialog.entity
                            # We found our most recent match from invite
                            break
                    if not entity:
                        print("Error: Channel not found in your chats.")
                        print("  Make sure you've joined the channel first.")
                        sys.exit(1)
            except (InviteHashInvalidError, InviteHashExpiredError) as e:
                print(f"Error: Invalid or expired invite link: {e}")
                sys.exit(1)
        else:
            print(f"Looking up channel: {channel_id}")
            try:
                entity = await client.get_entity(channel_id)
            except (UsernameNotOccupiedError, UsernameInvalidError, ValueError):
                print(f"Error: Channel not found: {channel_id}")
                sys.exit(1)
            except ChannelPrivateError:
                print(f"Error: No access to channel: {channel_id}")
                print("  Make sure you're a member of this channel.")
                sys.exit(1)

        # Get channel info
        if isinstance(entity, Channel):
            channel_title = entity.title
            entity_id = entity.id
        elif isinstance(entity, (Chat, User)):
            channel_title = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
            entity_id = entity.id
        else:
            channel_title = str(entity)
            entity_id = getattr(entity, 'id', 0)

        print(f"Channel: {channel_title}")
        print(f"Period: {start_date.date()} -> {end_date.date()}")
        print("Fetching messages...")

        messages = []
        count = 0

        try:
            async for msg in client.iter_messages(
                entity,
                offset_date=end_date,
                reverse=False,
            ):
                # Stop if we've gone past start_date
                if msg.date.replace(tzinfo=timezone.utc) < start_date:
                    break

                # Skip if after end_date
                if msg.date.replace(tzinfo=timezone.utc) > end_date:
                    continue

                count += 1
                if count % 100 == 0:
                    print(f"  ...fetched {count} messages")

                msg_data = {
                    "id": msg.id,
                    "date": msg.date.isoformat(),
                    "text": msg.text or "",
                    "views": getattr(msg, 'views', None),
                    "forwards": getattr(msg, 'forwards', None),
                    "replies": getattr(msg.replies, 'replies', None) if msg.replies else None,
                }

                if msg.media:
                    msg_data["media_type"] = type(msg.media).__name__

                if msg.entities:
                    urls = []
                    for ent in msg.entities:
                        if hasattr(ent, 'url') and ent.url:
                            urls.append(ent.url)
                    if urls:
                        msg_data["urls"] = urls

                if msg.forward:
                    msg_data["forwarded"] = True
                    if msg.forward.chat:
                        msg_data["forward_from"] = getattr(msg.forward.chat, 'title', str(msg.forward.chat))

                messages.append(msg_data)

        except FloodWaitError as e:
            print(f"Warning: Rate limit hit - Telegram requires {e.seconds}s wait")
            print(f"  Saving {len(messages)} messages fetched so far...")

        # Reverse to chronological order
        messages.reverse()

        export_data = {
            "channel": {
                "input": channel_input,
                "title": channel_title,
                "id": entity_id,
            },
            "export_info": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "message_count": len(messages),
            },
            "messages": messages,
        }

        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"Exported {len(messages)} messages")
        print(f"Saved to: {output_file}")

        return export_data


def main():
    parser = argparse.ArgumentParser(
        description="Export Telegram channel messages for a date range"
    )
    parser.add_argument(
        "--channel", "-c",
        required=True,
        help="Channel (@name, t.me/name, or invite link)"
    )
    parser.add_argument(
        "--start-date", "-s",
        required=True,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", "-e",
        required=True,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output JSON file path"
    )

    args = parser.parse_args()

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date).replace(hour=23, minute=59, second=59)

    if start_date > end_date:
        print("Error: Start date must be before end date")
        sys.exit(1)

    asyncio.run(export_channel(
        channel=args.channel,
        start_date=start_date,
        end_date=end_date,
        output_path=args.output,
    ))


if __name__ == "__main__":
    main()
