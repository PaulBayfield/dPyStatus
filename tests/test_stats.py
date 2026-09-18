from datetime import UTC, datetime, timedelta

import pytest

from dPyStatus import build_payload, collect_shards, collect_stats, get_status

from .conftest import FakeBot, FakeShard, make_guild


def test_collect_stats(bot: FakeBot) -> None:
    stats = collect_stats(bot)

    assert stats["guilds"] == 2
    assert stats["users"] == 100
    assert stats["cached_users"] == 42
    assert stats["shard_count"] == 1
    assert stats["channels"] == {
        "total": 10,
        "text": 4,
        "voice": 2,
        "stage": 1,
        "category": 1,
        "forum": 1,
        "other": 1,
        "threads": 2,
    }


@pytest.mark.parametrize(
    ("ready", "closed", "shards", "expected"),
    [
        (True, False, None, "online"),
        (False, False, None, "starting"),
        (True, True, None, "offline"),
        (True, False, {0: FakeShard(0), 1: FakeShard(1, closed=True)}, "degraded"),
        (True, False, {0: FakeShard(0), 1: FakeShard(1)}, "online"),
    ],
)
def test_get_status(ready: bool, closed: bool, shards: dict | None, expected: str) -> None:
    assert get_status(FakeBot(ready=ready, closed=closed, shards=shards)) == expected


def test_collect_shards_single() -> None:
    bot = FakeBot(guilds=[make_guild(), make_guild()], latency=float("inf"))
    assert collect_shards(bot) == [{"id": 0, "latency_ms": None, "closed": False, "guilds": 2}]


def test_collect_shards_auto_sharded() -> None:
    bot = FakeBot(
        guilds=[make_guild(shard_id=0), make_guild(shard_id=1), make_guild(shard_id=1)],
        shard_count=2,
        shards={1: FakeShard(1, latency=0.1234, closed=True), 0: FakeShard(0, latency=0.05)},
    )
    assert collect_shards(bot) == [
        {"id": 0, "latency_ms": 50.0, "closed": False, "guilds": 1},
        {"id": 1, "latency_ms": 123.4, "closed": True, "guilds": 2},
    ]


def test_build_payload(bot: FakeBot) -> None:
    ready_at = datetime.now(UTC) - timedelta(minutes=5)
    payload = build_payload(bot, ready_at=ready_at, extra={"foo": 1})

    assert payload["status"] == "online"
    assert payload["ready"] is True
    assert payload["latency_ms"] == 42.0
    assert payload["ready_at"] == ready_at.isoformat()
    assert 299 < payload["uptime"] < 310
    assert payload["user"] == {"id": "123456789012345678", "name": "CROUStillant"}
    assert payload["extra"] == {"foo": 1}
    assert set(payload["versions"]) == {"python", "discord.py", "dPyStatus"}


def test_build_payload_before_login() -> None:
    payload = build_payload(FakeBot(ready=False, latency=float("nan")), ready_at=None)

    assert payload["status"] == "starting"
    assert payload["latency_ms"] is None
    assert payload["uptime"] is None
    assert payload["user"] is None
