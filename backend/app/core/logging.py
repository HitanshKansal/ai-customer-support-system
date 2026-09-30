"""Logging setup for the API service."""

import logging


def configure_logging(log_level: str) -> None:
    """Configure a consistent console logging format once at startup."""

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
