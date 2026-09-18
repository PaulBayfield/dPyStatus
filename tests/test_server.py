from __future__ import annotations

import socket

from collections.abc import AsyncIterator

import aiohttp
import pytest

from aiohttp.test_utils import TestClient, TestServer

from dPyStatus import StatusServer

from .conftest import FakeBot


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def make_client(server: StatusServer) -> TestClient:
    client = TestClient(TestServer(server.build_app()))
    await client.start_server()
    return client


@pytest.fixture
async def client(bot: FakeBot) -> AsyncIterator[TestClient]:
    client = await make_client(StatusServer(bot))
    yield client
    await client.close()


async def test_status_online(client: TestClient) -> None:
    response = await client.get("/status")

    assert response.status == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = await response.json()
    assert body["status"] == "online"
    assert body["stats"]["guilds"] == 2
    assert body["uptime"] is not None


async def test_status_head(client: TestClient) -> None:
    response = await client.head("/status")
    assert response.status == 200


@pytest.mark.parametrize(("ready", "closed"), [(False, False), (True, True)])
async def test_status_unavailable(ready: bool, closed: bool) -> None:
    client = await make_client(StatusServer(FakeBot(ready=ready, closed=closed)))
    try:
        response = await client.get("/status")
        assert response.status == 503
    finally:
        await client.close()


async def test_custom_path(bot: FakeBot) -> None:
    client = await make_client(StatusServer(bot, path="health"))
    try:
        assert (await client.get("/health")).status == 200
        assert (await client.get("/status")).status == 404
    finally:
        await client.close()


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({}, 401),
        ({"Authorization": "Bearer wrong"}, 401),
        ({"Authorization": "Basic secret"}, 401),
        ({"Authorization": "Bearer secret"}, 200),
        ({"Authorization": "bearer secret"}, 200),
    ],
)
async def test_token(bot: FakeBot, headers: dict[str, str], expected: int) -> None:
    client = await make_client(StatusServer(bot, token="secret"))
    try:
        response = await client.get("/status", headers=headers)
        assert response.status == expected
        if expected == 401:
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert await response.json() == {"error": "unauthorized"}
    finally:
        await client.close()


async def test_extras(bot: FakeBot) -> None:
    server = StatusServer(bot)

    @server.extra
    def sync_value() -> int:
        return 1

    @server.extra("database")
    async def check_database() -> bool:
        return True

    @server.extra()
    def broken() -> None:
        raise RuntimeError("boom")

    server.add_extra("removed", lambda: "nope")
    server.remove_extra("removed")

    client = await make_client(server)
    try:
        body = await (await client.get("/status")).json()
        assert body["extra"] == {"sync_value": 1, "database": True, "broken": None}
    finally:
        await client.close()


async def test_lifecycle(bot: FakeBot) -> None:
    port = free_port()
    server = StatusServer(bot, port=port)

    async with server:
        assert server.is_running
        assert server.ready_at is not None
        assert bot.listeners == [(server._on_ready, "on_ready")]
        await server.start()  # idempotent

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/status") as response:
                assert response.status == 200

    assert not server.is_running
    assert bot.listeners == []
    await server.stop()  # idempotent


async def test_ready_listener_sets_ready_at() -> None:
    bot = FakeBot(ready=False)
    server = StatusServer(bot, port=free_port())

    async with server:
        assert server.ready_at is None
        await server._on_ready()
        first = server.ready_at
        await server._on_ready()  # reconnects keep the original ready time
        assert first is not None and server.ready_at == first


async def test_start_failure_cleans_up(bot: FakeBot) -> None:
    port = free_port()
    async with StatusServer(bot, port=port):
        other = StatusServer(FakeBot(), port=port)
        with pytest.raises(OSError):
            await other.start()
        assert not other.is_running
        assert other.bot.listeners == []
