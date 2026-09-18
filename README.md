# dPyStatus

A lightweight `GET /status` HTTP endpoint for [discord.py](https://github.com/Rapptz/discord.py) bots.

It runs an [aiohttp](https://docs.aiohttp.org) server inside the bot's own event loop (no thread, no extra dependency:
aiohttp already ships with discord.py) and exposes the bot's stats as JSON, so an external service can tell whether
the bot is online.

## Installation

```sh
uv add git+https://github.com/PaulBayfield/dPyStatus
```

## Usage

### As an extension (configured through environment variables)

```python
await bot.load_extension("dPyStatus.extension")
```

| Variable               | Default     | Description                                               |
| ---------------------- | ----------- | --------------------------------------------------------- |
| `DPYSTATUS_HOST`       | `127.0.0.1` | Interface to bind. Use `0.0.0.0` in Docker.               |
| `DPYSTATUS_PORT`       | `8080`      | Port to listen on.                                        |
| `DPYSTATUS_PATH`       | `/status`   | Route of the endpoint.                                    |
| `DPYSTATUS_TOKEN`      | _none_      | If set, requests must send `Authorization: Bearer <token>`. |
| `DPYSTATUS_ACCESS_LOG` | `false`     | Log every request.                                        |

### As a cog (explicit options)

```python
from dPyStatus import StatusCog


class MyBot(commands.Bot):
    async def setup_hook(self) -> None:
        await self.add_cog(StatusCog(self, host="0.0.0.0", port=8080, token="secret"))
```

The server starts when the cog is loaded and stops when it is unloaded or when the bot closes.

### Standalone

```python
from dPyStatus import StatusServer


class MyBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.status = StatusServer(self, host="0.0.0.0", port=8080)
        await self.status.start()

    async def close(self) -> None:
        await self.status.stop()
        await super().close()
```

`StatusServer` is also an async context manager (`async with StatusServer(bot): ...`), and works with a plain
`discord.Client` or `discord.AutoShardedClient` too.

### Extra values

Expose your own values under `extra`. Callbacks take no argument, may be sync or async, and must return something
JSON-serialisable. If one raises, its value is `null` and the error is logged on the `dPyStatus` logger.

```python
status = bot.get_cog("dPyStatus").server  # or your StatusServer instance


@status.extra
def version() -> str:
    return "3.0.0"


@status.extra("database")
async def database_ok() -> bool:
    return await bot.pool.fetchval("SELECT TRUE")


status.add_extra("restaurants", lambda: len(bot.restaurants))
status.remove_extra("restaurants")
```

### Examples

See [`examples/`](examples):

- [`extension.py`](examples/extension.py): load the extension, configured by environment variables.
- [`cog.py`](examples/cog.py): add the cog with explicit options and register extra values.
- [`standalone.py`](examples/standalone.py): `StatusServer` as a context manager with an `AutoShardedClient`.
- [`check.py`](examples/check.py): query the endpoint from an external service (exit code 0 if up).

## Response

`GET /status` (and `HEAD /status`) answers:

| Code  | `status`                | Meaning                          |
| ----- | ----------------------- | -------------------------------- |
| `200` | `online`                | The bot is ready.                |
| `200` | `degraded`              | Ready, but some shards are down. |
| `503` | `starting` / `offline`  | Not ready yet / closed.          |
| `401` | _n/a_                   | Missing or wrong token.          |

```json
{
  "status": "online",
  "ready": true,
  "latency_ms": 42.1,
  "ready_at": "2026-09-18T10:00:00.000000+00:00",
  "uptime": 3600.123,
  "timestamp": "2026-09-18T11:00:00.123000+00:00",
  "user": { "id": "123456789012345678", "name": "CROUStillant" },
  "stats": {
    "guilds": 120,
    "users": 45210,
    "cached_users": 3120,
    "channels": {
      "total": 2400, "text": 1500, "voice": 500, "stage": 10,
      "category": 350, "forum": 30, "other": 10, "threads": 80
    },
    "shard_count": 1
  },
  "shards": [{ "id": 0, "latency_ms": 42.1, "closed": false, "guilds": 120 }],
  "extra": { "database": true },
  "versions": { "python": "3.13.2", "discord.py": "2.7.1", "dPyStatus": "0.1.0" }
}
```

- `users` is the sum of `member_count` over guilds; `cached_users` is `len(bot.users)`.
- IDs are strings (they do not fit in a JavaScript number).
- `latency_ms` and `uptime` are `null` until the bot has connected.

## Development

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
