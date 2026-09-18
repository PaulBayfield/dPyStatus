"""
Query a dPyStatus endpoint from an external service, e.g. a monitor or a cron job.

    python examples/check.py http://127.0.0.1:8080/status secret

Exits with 0 when the bot is up (online or degraded), 1 otherwise.
"""

import asyncio
import sys

import aiohttp


async def check(url: str, token: str | None = None) -> bool:
    """
    Check whether the bot behind a dPyStatus endpoint is up.

    :param url: The full URL of the status endpoint.
    :type url: str
    :param token: The bearer token, if the endpoint requires one.
    :type token: str | None
    :return: ``True`` if the bot is online or degraded.
    :rtype: bool
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    timeout = aiohttp.ClientTimeout(total=5)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    print("Unauthorized: wrong or missing token")
                    return False

                data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as error:
        print(f"Unreachable: {error!r}")
        return False

    stats = data["stats"]
    print(
        f"{data['status']} - latency {data['latency_ms']} ms - uptime {data['uptime']} s - "
        f"{stats['guilds']} guilds, {stats['users']} users, {stats['channels']['total']} channels, "
        f"{stats['shard_count']} shard(s)"
    )
    for shard in data["shards"]:
        print(f"  shard {shard['id']}: {'down' if shard['closed'] else 'up'}, {shard['latency_ms']} ms")

    return response.status == 200


if __name__ == "__main__":
    ok = asyncio.run(check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    sys.exit(0 if ok else 1)
