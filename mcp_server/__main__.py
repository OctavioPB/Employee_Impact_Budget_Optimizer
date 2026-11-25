"""Run the EIBO MCP server.

    python -m mcp_server                          # stdio (Claude Desktop, Claude Code)
    python -m mcp_server --transport http         # Streamable HTTP on 127.0.0.1:8790/mcp

Identity and options come from environment variables (see mcp_server/config.py and
docs/MCP_SERVER.md). HTTP mode refuses to start without EIBO_MCP_TOKEN.
"""

from __future__ import annotations

import argparse
import hmac
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp_server.config import ConfigError, settings_from_env
from mcp_server.server import build_server


class BearerTokenMiddleware:
    """Reject HTTP requests that do not carry `Authorization: Bearer <EIBO_MCP_TOKEN>`."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            supplied = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, self.expected):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mcp_server", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address (default: localhost only)")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args(argv)

    # stdout carries the MCP protocol in stdio mode: all logging goes to stderr.
    logging.basicConfig(stream=sys.stderr, level=os.getenv("LOG_LEVEL", "WARNING"))

    try:
        settings = settings_from_env()
    except ConfigError as exc:
        print(f"eibo-mcp: configuration error: {exc}", file=sys.stderr)
        return 2

    server = build_server(settings)
    if args.transport == "stdio":
        server.run("stdio")
        return 0

    token = os.getenv("EIBO_MCP_TOKEN", "")
    if len(token) < 32:
        print("eibo-mcp: HTTP mode needs EIBO_MCP_TOKEN (at least 32 characters).", file=sys.stderr)
        return 2
    import uvicorn

    app = BearerTokenMiddleware(server.streamable_http_app(host=args.host), token)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
