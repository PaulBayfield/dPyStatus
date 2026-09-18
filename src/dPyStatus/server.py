from __future__ import annotations

import hmac
import inspect
import logging

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, overload

from aiohttp import web

from .stats import build_payload

if TYPE_CHECKING:
    from types import TracebackType

    from discord import Client


ExtraCallback = Callable[[], Any | Awaitable[Any]]

log = logging.getLogger("dPyStatus")


class StatusServer:
    """
    A lightweight HTTP server exposing a ``GET /status`` endpoint for a discord.py bot.

    The server runs inside the bot's event loop, so it needs no extra thread or process.
    The endpoint answers ``200`` when the bot is ready (``online`` or ``degraded``) and ``503``
    otherwise (``starting`` or ``offline``), so a monitor can rely on the HTTP code alone.

    Usage::

        status = StatusServer(bot, host="0.0.0.0", port=8080, token="secret")

        @status.extra
        async def database() -> bool:
            return await pool.fetchval("SELECT TRUE")

        await status.start()
        ...
        await status.stop()
    """

    def __init__(
        self,
        bot: Client,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
        path: str = "/status",
        token: str | None = None,
        access_log: bool = False,
    ) -> None:
        """
        Create the status server (it is not started until :meth:`start` is awaited).

        :param bot: The discord.py client or bot to report on.
        :type bot: discord.Client
        :param host: Interface to bind to. Use ``0.0.0.0`` to expose it outside the host (e.g. in Docker).
        :type host: str
        :param port: Port to listen on.
        :type port: int
        :param path: Route of the status endpoint.
        :type path: str
        :param token: If set, requests must send ``Authorization: Bearer <token>``.
        :type token: str | None
        :param access_log: Log every request through aiohttp's access logger.
        :type access_log: bool
        """
        self.bot = bot
        self.host = host
        self.port = port
        self.path = path if path.startswith("/") else f"/{path}"
        self.token = token
        self.access_log = access_log

        self.ready_at: datetime | None = None
        self._extras: dict[str, ExtraCallback] = {}
        self._runner: web.AppRunner | None = None

    # ------------------------------------------------------------------ extras

    @overload
    def extra(self, name: ExtraCallback, /) -> ExtraCallback: ...

    @overload
    def extra(self, name: str | None = None, /) -> Callable[[ExtraCallback], ExtraCallback]: ...

    def extra(self, name: str | ExtraCallback | None = None, /) -> Any:
        """
        Decorator registering a custom value exposed under ``extra`` in the payload.

        The callback takes no argument, may be sync or async, and must return a JSON-serialisable value.
        If it raises, the value is ``null`` and the error is logged.

        Usage::

            @status.extra
            def version() -> str: ...

            @status.extra("db")
            async def database_ok() -> bool: ...

        :param name: Key in the ``extra`` object (defaults to the function name), or the function itself
            when used without parentheses.
        :type name: str | Callable[[], Any] | None
        :return: The decorated function, or a decorator when called with a name.
        :rtype: Callable[[], Any] | Callable[[Callable[[], Any]], Callable[[], Any]]
        """
        if callable(name):
            self.add_extra(name.__name__, name)
            return name

        def decorator(func: ExtraCallback) -> ExtraCallback:
            self.add_extra(name or func.__name__, func)
            return func

        return decorator

    def add_extra(self, name: str, func: ExtraCallback) -> None:
        """
        Register a custom value exposed under ``extra.<name>`` in the payload.

        :param name: Key in the ``extra`` object.
        :type name: str
        :param func: A sync or async callable taking no argument.
        :type func: Callable[[], Any | Awaitable[Any]]
        """
        self._extras[name] = func

    def remove_extra(self, name: str) -> None:
        """
        Unregister a custom value, if present.

        :param name: Key in the ``extra`` object.
        :type name: str
        """
        self._extras.pop(name, None)

    async def _collect_extras(self) -> dict[str, Any]:
        """
        Call every registered extra callback.

        :return: The value of each callback, ``None`` for those that raised.
        :rtype: dict[str, Any]
        """
        values: dict[str, Any] = {}
        for name, func in self._extras.items():
            try:
                value = func()
                if inspect.isawaitable(value):
                    value = await value
            except Exception:
                log.exception("dPyStatus extra %r raised an exception", name)
                value = None
            values[name] = value
        return values

    # ------------------------------------------------------------------ http

    def _is_authorized(self, request: web.Request) -> bool:
        """
        Check the bearer token of a request.

        :param request: The aiohttp request.
        :type request: aiohttp.web.Request
        :return: ``True`` if no token is configured or if the request sends the right one.
        :rtype: bool
        """
        if self.token is None:
            return True
        scheme, _, credentials = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer":
            return False
        return hmac.compare_digest(credentials.strip().encode(), self.token.encode())

    async def handle_status(self, request: web.Request) -> web.Response:
        """
        Handle ``GET``/``HEAD`` requests on the status route.

        :param request: The aiohttp request.
        :type request: aiohttp.web.Request
        :return: The JSON status, with ``200`` if the bot is ready, ``503`` otherwise and ``401`` on a bad token.
        :rtype: aiohttp.web.Response
        """
        if not self._is_authorized(request):
            return web.json_response(
                {"error": "unauthorized"},
                status=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if self.ready_at is None and self.bot.is_ready():
            self.ready_at = datetime.now(UTC)

        payload = build_payload(self.bot, ready_at=self.ready_at, extra=await self._collect_extras())
        code = 200 if payload["status"] in ("online", "degraded") else 503
        return web.json_response(payload, status=code, headers={"Cache-Control": "no-store"})

    def build_app(self) -> web.Application:
        """
        Build the aiohttp application (also useful to mount it in tests or in another app).

        :return: The aiohttp application serving the status route.
        :rtype: aiohttp.web.Application
        """
        app = web.Application()
        app.router.add_get(self.path, self.handle_status)
        return app

    # ------------------------------------------------------------------ lifecycle

    async def _on_ready(self) -> None:
        """Record when the bot first became ready (reconnections keep the original time)."""
        if self.ready_at is None:
            self.ready_at = datetime.now(UTC)

    def _add_ready_listener(self) -> None:
        """Listen to ``on_ready``; with a plain Client, ``ready_at`` is set lazily on the first request."""
        if hasattr(self.bot, "add_listener"):
            self.bot.add_listener(self._on_ready, "on_ready")

    def _remove_ready_listener(self) -> None:
        """Stop listening to ``on_ready``."""
        if hasattr(self.bot, "remove_listener"):
            self.bot.remove_listener(self._on_ready, "on_ready")

    @property
    def is_running(self) -> bool:
        """
        Whether the HTTP server is currently listening.

        :rtype: bool
        """
        return self._runner is not None

    async def start(self) -> None:
        """
        Start listening. Calling it while already running does nothing.

        :raises OSError: If the port cannot be bound.
        """
        if self._runner is not None:
            return

        if self.bot.is_ready() and self.ready_at is None:
            self.ready_at = datetime.now(UTC)
        self._add_ready_listener()

        runner = web.AppRunner(self.build_app(), access_log=log if self.access_log else None)
        await runner.setup()
        try:
            await web.TCPSite(runner, self.host, self.port).start()
        except BaseException:
            await runner.cleanup()
            self._remove_ready_listener()
            raise

        self._runner = runner
        log.info("dPyStatus listening on http://%s:%s%s", self.host, self.port, self.path)

    async def stop(self) -> None:
        """Stop listening. Calling it while not running does nothing."""
        if self._runner is None:
            return

        runner, self._runner = self._runner, None
        self._remove_ready_listener()
        await runner.cleanup()
        log.info("dPyStatus stopped")

    async def __aenter__(self) -> StatusServer:
        """
        Start the server when entering an ``async with`` block.

        :return: The started server.
        :rtype: StatusServer
        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """
        Stop the server when leaving an ``async with`` block.

        :param exc_type: The exception type, if any.
        :type exc_type: type[BaseException] | None
        :param exc: The exception, if any.
        :type exc: BaseException | None
        :param tb: The traceback, if any.
        :type tb: types.TracebackType | None
        """
        await self.stop()
