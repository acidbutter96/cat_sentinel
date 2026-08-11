from __future__ import annotations

import uvicorn

from app.settings.config import settings


def main() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.http_port, reload=False)


if __name__ == "__main__":
    main()
