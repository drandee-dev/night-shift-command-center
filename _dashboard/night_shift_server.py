"""Serve Night Shift alone: the action endpoint and the live-state API for the dashboard note.

    python night_shift_server.py            # http://127.0.0.1:8790
    python night_shift_server.py --port 9000

The same routes app.py mounts inside the full vault dashboard (nightshift_api.py). Loopback only, on purpose: the token
is a guard between programs on this PC, not a login for the network. Any other bind address is refused. Each start
writes a new token to nightshift_api.TOKEN_FILE.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

import actions  # noqa: E402
import nightshift_api  # noqa: E402

DEFAULT_PORT = 8790
LOOPBACK = ("127.0.0.1", "localhost")


def create_app(runner: actions.Runner | None = None, token: str | None = None) -> FastAPI:
    app = FastAPI(title="Night Shift", docs_url=None, redoc_url=None, openapi_url=None)
    nightshift_api.register(app, runner or actions.Runner(), token or nightshift_api.new_token())
    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.host not in LOOPBACK:
        print(f"refusing to bind {args.host}: loopback only", file=sys.stderr)
        return 2
    print(f"Night Shift on http://{args.host}:{args.port}  (ctrl-c to stop)")
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
