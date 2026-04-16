"""pull-cord: Discord channel client with pagination and rate limiting."""

import os
import time
from datetime import datetime, timezone

import requests

DISCORD_EPOCH = 1420070400000


def snowflake_to_timestamp_ms(snowflake_id):
    """Convert a Discord snowflake ID to a Unix timestamp in milliseconds."""
    return (int(snowflake_id) >> 22) + DISCORD_EPOCH


def snowflake_to_utc_str(snowflake_id):
    """Convert a Discord snowflake ID to a UTC timestamp string."""
    ts_ms = snowflake_to_timestamp_ms(snowflake_id)
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def date_to_snowflake(dt):
    """Convert a datetime to a Discord snowflake ID (useful for range queries)."""
    timestamp_ms = int(dt.timestamp() * 1000)
    return (timestamp_ms - DISCORD_EPOCH) << 22


class DiscordClient:
    """Fetch messages from a Discord channel with pagination and rate limiting.

    Requires a bot token with the `Read Message History` permission.

    Usage:
        with DiscordClient(token="...", channel_id="...") as client:
            for batch in client.fetch_batches():
                for message in batch:
                    print(message["content"])
    """

    def __init__(self, token, channel_id):
        """
        Args:
            token: Discord bot token.
            channel_id: ID of the channel to read from.
        """
        self.channel_id = channel_id
        self.base_url = f'https://discord.com/api/v9/channels/{self.channel_id}/messages'
        self.session = requests.Session()
        self.session.headers['Authorization'] = token

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _fetch_batch(self, before=None, after=None, _retries=0):
        """Fetch up to 100 messages, handling rate limits and auth errors."""
        params = {'limit': 100}
        if before is not None:
            params['before'] = str(before)
        if after is not None:
            params['after'] = str(after)

        resp = self.session.get(self.base_url, params=params)

        if resp.status_code == 401:
            raise PermissionError('Discord token is invalid or expired.')

        if resp.status_code == 429:
            if _retries >= 5:
                raise RuntimeError('Rate limited too many times — aborting.')
            try:
                retry_after = resp.json().get('retry_after', 5)
            except Exception:
                retry_after = 5
            time.sleep(retry_after)
            return self._fetch_batch(before=before, after=after, _retries=_retries + 1)

        resp.raise_for_status()
        return resp.json()

    def fetch_batches(self, before_snowflake=None, after_snowflake=None):
        """Paginate backward through channel history.

        Args:
            before_snowflake: Upper bound snowflake ID (exclusive). Defaults to
                the most recent message.
            after_snowflake: Lower bound snowflake ID (inclusive). Pagination
                stops when this ID is reached.

        Yields:
            Lists of message dicts (Discord API format), newest-first within
            each batch, batches yielded from newest to oldest.
        """
        current_before = before_snowflake

        while True:
            batch = self._fetch_batch(before=current_before)

            if not batch:
                break

            if after_snowflake is not None:
                filtered = [m for m in batch if int(m['id']) >= int(after_snowflake)]
                hit_lower_bound = len(filtered) < len(batch)
                batch = filtered
            else:
                hit_lower_bound = False

            if batch:
                yield batch

            if hit_lower_bound or len(batch) < 100:
                break

            current_before = batch[-1]['id']
            time.sleep(1.5)

    def fetch_batches_forward(self, after_snowflake):
        """Paginate forward through channel history from a given point.

        Useful for incremental syncs — pick up where you left off by passing
        the snowflake ID of the last message you processed.

        Args:
            after_snowflake: Lower bound snowflake ID (exclusive). Only
                messages newer than this ID are returned.

        Yields:
            Lists of message dicts (Discord API format), oldest-first within
            each batch, batches yielded from oldest to newest.
        """
        current_after = after_snowflake

        while True:
            batch = self._fetch_batch(after=current_after)

            if not batch:
                break

            yield batch

            if len(batch) < 100:
                break

            current_after = batch[0]['id']
            time.sleep(1.5)
