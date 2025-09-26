# Copilot Instructions for TG_scraper

This is a Telegram Channel Scraper that extracts messages from Telegram channels into structured CSV files using the Telethon library.

## Architecture Overview

- **Single Script Design**: All functionality is contained in `tg_scraper.py` - a monolithic CLI tool that handles authentication, message extraction, and CSV export
- **Session-Based Authentication**: Uses Telethon's session persistence (`session_scraper.session`) to maintain authentication state across runs
- **CSV Data Pipeline**: Extracts messages → processes metadata → exports to structured CSV with predefined column order

## Key Patterns & Conventions

### Date Handling
- **Brussels Timezone Default**: All input dates are assumed to be Europe/Brussels timezone, then converted to UTC for processing
- **Flexible Date Formats**: Supports both `YYYY-MM-DD HH:MM:SS` and `DD-MM-YYYY HH:MM:SS` input formats via `parse_local_datetime()`
- **UTC Storage**: All timestamps stored in CSV as ISO format UTC (`date_iso` column)

### Message Processing
- **Rich Metadata Extraction**: Each message captures views, forwards, replies, media types, URLs, and document filenames
- **URL Extraction**: Dual approach using Telethon entities + regex fallback for comprehensive link detection
- **Media Detection**: Identifies photos, videos, documents with filename extraction from `DocumentAttributeFilename`

### Error Handling & Rate Limiting
- **Flood Wait Recovery**: Automatically handles Telegram rate limits with `FloodWaitError` detection and retry logic
- **Graceful Entity Resolution**: Falls back to link-based permalinks when usernames are unavailable
- **Exception Isolation**: Continues processing other messages even if individual messages fail

### CSV Structure
```
Username, Account, Platform, ChannelLink, id, date_iso, permalink, 
text, urls, media_types, document_filenames, album_group_id, 
views, forwards, replies_count
```

## Development Workflows

### Running the Scraper
```bash
python tg_scraper.py --channel https://t.me/channelname --since "2024-01-01 00:00:00" --end "2024-12-31 23:59:59" --output output.csv
```

### API Credentials Setup
- Replace `api_id` and `api_hash` constants in `tg_scraper.py` with your Telegram API credentials
- First run will prompt for phone number and authentication code
- Session file persists authentication for subsequent runs

### Data Analysis Patterns
- CSV files use JSON encoding for complex fields (`urls`, `media_types`, `document_filenames`)
- Use `pd.read_csv()` with `json.loads()` to parse these fields for analysis
- `album_group_id` links related media messages together

## Important Constraints

- **No Batch Processing**: Single channel per execution - no multi-channel support
- **Memory Intensive**: All messages loaded into DataFrame before CSV export
- **No Incremental Updates**: Always full date range extraction, no append mode
- **Hardcoded Constants**: Platform name, timezone, and session name are fixed in code

## Files to Modify When

- **`tg_scraper.py`**: All functionality changes, new extraction fields, error handling improvements
- **`README.md`**: Usage instructions, dependency updates, example modifications  
- **CSV files**: Data outputs only - never edit manually (regenerate via script)
- **`.session` file**: Delete to force re-authentication, never commit to version control