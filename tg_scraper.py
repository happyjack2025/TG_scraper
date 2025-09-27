# Telegram Channel Scraper — CLI-driven with --output
# Requires: pip install telethon pandas pytz

import asyncio
import argparse
import pandas as pd
import pytz
import re
import json
from typing import Optional, List, Tuple
from datetime import datetime
from telethon import TelegramClient, errors
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl, DocumentAttributeFilename

# ======================= USER CONFIG =======================

api_id = 12345
api_hash = '1234ccc222ddd333zzz'

PlatformName = 'Telegram'
SESSION_NAME = 'session_scraper'
BRUSSELS_TZ = pytz.timezone('Europe/Brussels')
client = TelegramClient(SESSION_NAME, api_id, api_hash)

# ====================== HELPER FUNCTIONS ======================

def parse_local_datetime(dt_str: str) -> datetime:
    dt_str = dt_str.strip()
    fmts = ['%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S']
    last_err = None
    for fmt in fmts:
        try:
            naive = datetime.strptime(dt_str, fmt)
            local_dt = BRUSSELS_TZ.localize(naive)
            return local_dt.astimezone(pytz.utc)
        except Exception as e:
            last_err = e
    raise ValueError(f"Could not parse date '{dt_str}': {last_err}")

def in_range(ts_utc: datetime, since_utc: datetime, until_utc: Optional[datetime]) -> bool:
    if ts_utc < since_utc:
        return False
    if until_utc is not None and ts_utc > until_utc:
        return False
    return True

def extract_urls_from_message(text: Optional[str], entities) -> List[str]:
    seen = set()
    urls: List[str] = []
    if entities and text:
        for ent in entities:
            if isinstance(ent, MessageEntityTextUrl):
                url = ent.url
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
            elif isinstance(ent, MessageEntityUrl):
                try:
                    url = text[ent.offset: ent.offset + ent.length]
                    if url and url not in seen:
                        seen.add(url)
                        urls.append(url)
                except Exception:
                    pass
    if text:
        for match in re.findall(r'https?://\S+', text):
            cleaned = match.rstrip(').,;]}>\'"')
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                urls.append(cleaned)
    return urls

def detect_media(m) -> Tuple[List[str], List[str], Optional[int]]:
    kinds: List[str] = []
    doc_fns: List[str] = []
    if getattr(m, 'photo', None):
        kinds.append('photo')
    if getattr(m, 'video', None):
        kinds.append('video')
    if getattr(m, 'document', None):
        kinds.append('document')
        try:
            for attr in m.document.attributes or []:
                if isinstance(attr, DocumentAttributeFilename) and attr.file_name:
                    doc_fns.append(attr.file_name)
        except Exception:
            pass
    return kinds, doc_fns, getattr(m, 'grouped_id', None)

async def get_channel_entity(channel_ref: str):
    try:
        entity = await client.get_entity(channel_ref)
        title = getattr(entity, 'title', None) or getattr(entity, 'first_name', '') or 'Unknown'
        username = getattr(entity, 'username', None)
        return entity, title, username
    except errors.UsernameNotOccupiedError as e:
        print(f"[ERROR] UsernameNotOccupiedError for {channel_ref}: {e}")
    except errors.FloodWaitError as e:
        print(f"[RATE LIMIT] Flood wait {e.seconds}s while resolving {channel_ref}")
        await asyncio.sleep(e.seconds + 1)
        return await get_channel_entity(channel_ref)
    except Exception as e:
        print(f"[ERROR] get_channel_entity({channel_ref}): {e}")
    return None, None, None

# ======================= SCRAPE LOGIC =======================

async def fetch_channel_messages(entity,
                                 since_dt_utc: datetime,
                                 until_dt_utc: Optional[datetime],
                                 link_for_building: str,
                                 entity_title: str,
                                 platform_name: str) -> pd.DataFrame:
    rows = []
    try:
        async for m in client.iter_messages(entity, reverse=True):
            if not m or not getattr(m, 'date', None):
                continue
            if not in_range(m.date, since_dt_utc, until_dt_utc):
                continue

            text = m.message or ""
            views = getattr(m, 'views', None)
            forwards = getattr(m, 'forwards', None)
            replies = getattr(getattr(m, 'replies', None), 'replies', None)

            urls = extract_urls_from_message(text, getattr(m, 'entities', None))
            media_types, doc_filenames, album_group_id = detect_media(m)

            username = getattr(entity, 'username', None)
            permalink = f"https://t.me/{username}/{m.id}" if username else f"{link_for_building.rstrip('/')}/{m.id}"

            rows.append({
                'Username': username or link_for_building.split('/')[-1],
                'Account': entity_title,
                'Platform': platform_name,
                'ChannelLink': link_for_building,
                'id': m.id,
                'date_iso': m.date.isoformat(),
                'permalink': permalink,
                'text': text,
                'urls': json.dumps(urls, ensure_ascii=False),
                'media_types': json.dumps(media_types, ensure_ascii=False),
                'document_filenames': json.dumps(doc_filenames, ensure_ascii=False),
                'album_group_id': album_group_id,
                'views': views,
                'forwards': forwards,
                'replies_count': replies
            })

    except errors.FloodWaitError as e:
        print(f"[RATE LIMIT] Flood wait {e.seconds}s while reading {entity_title}")
        await asyncio.sleep(e.seconds + 1)
        return await fetch_channel_messages(entity, since_dt_utc, until_dt_utc,
                                            link_for_building, entity_title, platform_name)
    except Exception as e:
        print(f"[ERROR] fetch_channel_messages({entity_title}): {e}")

    df = pd.DataFrame(rows)
    if not df.empty:
        desired_order = [
            'Username', 'Account', 'Platform', 'ChannelLink',
            'id', 'date_iso', 'permalink',
            'text', 'urls', 'media_types', 'document_filenames', 'album_group_id',
            'views', 'forwards', 'replies_count'
        ]
        remaining = [c for c in df.columns if c not in desired_order]
        df = df[desired_order + remaining]
    return df

# =========================== MAIN ============================

async def main(args):
    await client.start()

    since_dt = parse_local_datetime(args.since)
    until_dt = parse_local_datetime(args.end) if args.end else None

    print(f"Date window (UTC): since={since_dt.isoformat()} until={(until_dt.isoformat() if until_dt else 'open-ended')}")

    entity, title, username = await get_channel_entity(args.channel)
    if not entity:
        print(f"Failed to resolve {args.channel}")
        return

    print(f"Scraping: {title} ({username or 'no-username'})")

    df = await fetch_channel_messages(
        entity=entity,
        since_dt_utc=since_dt,
        until_dt_utc=until_dt,
        link_for_building=args.channel,
        entity_title=title,
        platform_name=PlatformName
    )

    if df.empty:
        print("No messages found in the selected window.")
    else:
        df.to_csv(args.output, index=False, encoding='utf-8')
        print(f"\nSaved CSV: {args.output}")

    await client.disconnect()

# ========================== ENTRY ============================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape Telegram channel messages to CSV.")
    parser.add_argument('--channel', required=True, help="Channel link (e.g. https://t.me/PrivateCanadianNews)")
    parser.add_argument('--since', required=True, help="Start date (YYYY-MM-DD HH:MM:SS or DD-MM-YYYY HH:MM:SS)")
    parser.add_argument('--end', required=False, help="End date (optional, same formats)")
    parser.add_argument('--output', required=True, help="Output CSV filename (e.g. C:\\DemoProject\\output.csv)")
    args = parser.parse_args()

    asyncio.run(main(args))
    print('Done.')
