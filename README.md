# pull-cord

A single-file Discord message fetcher. Handles pagination and rate limits so you don't have to.

## Setup

```bash
pip install requests python-dotenv
```

Copy `pull_cord.py` into your project, then set up your token:

```bash
cp .env.example .env
# add your bot token to .env
```

## Usage

```python
import os
from dotenv import load_dotenv
from pull_cord import DiscordClient

load_dotenv()

with DiscordClient(token=os.getenv("DISCORD_TOKEN"), channel_id="881234567890123456") as client:
    for batch in client.fetch_batches():
        for message in batch:
            print(message["id"], message["content"])
```

### Fetch a date range

```python
from datetime import datetime, timezone
from pull_cord import date_to_snowflake

start = date_to_snowflake(datetime(2024, 1, 1, tzinfo=timezone.utc))
end   = date_to_snowflake(datetime(2024, 2, 1, tzinfo=timezone.utc))

# same client setup as above
for batch in client.fetch_batches(before_snowflake=end, after_snowflake=start):
    for message in batch:
        print(message["content"])
```

### Incremental sync

```python
last_seen_id = "1234567890"

for batch in client.fetch_batches_forward(after_snowflake=last_seen_id):
    for message in batch:
        process(message)
        last_seen_id = message["id"]
```

## API

### `DiscordClient(token, channel_id)`

| Method                                                       | What it does                                    |
| ------------------------------------------------------------ | ----------------------------------------------- |
| `fetch_batches(before_snowflake=None, after_snowflake=None)` | Paginate backward through history, newest first |
| `fetch_batches_forward(after_snowflake)`                     | Paginate forward from a given message           |

Both yield lists of message dicts, 100 messages per batch.

### Snowflake utilities

| Function                                  | Conversion                           |
| ----------------------------------------- | ------------------------------------ |
| `snowflake_to_timestamp_ms(snowflake_id)` | snowflake → Unix ms                  |
| `snowflake_to_utc_str(snowflake_id)`      | snowflake → `"2024-01-15T12:00:00Z"` |
| `date_to_snowflake(dt)`                   | datetime → snowflake                 |

## Notes

- Your bot needs Read Message History permission
- Rate limits are handled automatically with exponential backoff
