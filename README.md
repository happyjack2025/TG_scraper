# Telegram Channel Scraper

A small CLI that uses [Telethon](https://github.com/LonamiWebs/Telethon) to export messages from a Telegram channel into a CSV file.

## Requirements
- Python 3.10+
- [Telethon](https://pypi.org/project/Telethon/)
- [pandas](https://pypi.org/project/pandas/)
- [pytz](https://pypi.org/project/pytz/)

Install dependencies with:

```bash
pip install telethon pandas pytz
```

## Usage

```bash
python tg_scraper.py \
  --channel https://t.me/exampleChannel \
  --since "2024-01-01 00:00:00" \
  --end "2024-01-31 23:59:59" \
  --output ./output.csv
```

Arguments:
- `--channel`: Link to the Telegram channel to scrape (required).
- `--since`: Start of the UTC scraping window (`YYYY-MM-DD HH:MM:SS` or `DD-MM-YYYY HH:MM:SS`, required).
- `--end`: End of the UTC scraping window (optional, same formats as `--since`).
- `--output`: Destination CSV file path (required).

## Notes
- The script expects valid Telegram API credentials in `tg_scraper.py`. Replace the sample `api_id` and `api_hash` with your own values.
- The session file (`session_scraper.session`) is created automatically by Telethon; you can safely remove it before publishing if it contains sensitive data.
- CSV exports can grow quickly for large channels; consider ignoring raw datasets when versioning.
