"""CLI entry point for running the Python Robot Service."""

from __future__ import annotations

import argparse
import os

import uvicorn

from .api import create_app
from .service import create_robot_service


def resolve_model() -> str:
    model = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
    if ":" in model:
        return model
    provider = os.environ.get("LLM_PROVIDER", "google")
    return f"{provider}:{model}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mcar Python Robot Service")
    parser.add_argument("--host", default=os.environ.get("WEB_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEB_PORT", "8080")))
    parser.add_argument("--mock", action="store_true", default=os.environ.get("MCAR_MOCK") == "1")
    parser.add_argument("--model", default=resolve_model())
    args = parser.parse_args()

    service = create_robot_service(mock=args.mock, agent_model=args.model)
    uvicorn.run(create_app(service), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
