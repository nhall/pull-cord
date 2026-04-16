# pull-cord

Single-file Discord channel client. The entire implementation is in `pull_cord.py`.

## What it does

Fetches messages from a Discord channel via the REST API with:
- Backward pagination (`fetch_batches`) — walk back through history
- Forward pagination (`fetch_batches_forward`) — incremental sync from a checkpoint
- Automatic rate limit handling (429 backoff, up to 5 retries)
- Snowflake ↔ datetime conversion utilities

## Key facts

- Uses the Discord REST API v9 (`/channels/{id}/messages`)
- Requires a bot token with `Read Message History` permission
- No async — plain `requests` with `time.sleep` between batches (1.5s)
- The `Bot ` prefix in the Authorization header is required for bot tokens
- Discord snowflake IDs encode a timestamp: `(snowflake >> 22) + DISCORD_EPOCH`
- `DISCORD_EPOCH = 1420070400000` (Jan 1 2015 UTC in milliseconds)
- `fetch_batches` yields newest-first within each batch; `fetch_batches_forward` yields oldest-first

## Do not

- Add async support without being asked — the sync version is intentionally simple
- Add dependencies beyond `requests`
- Store the token anywhere other than what the caller provides
