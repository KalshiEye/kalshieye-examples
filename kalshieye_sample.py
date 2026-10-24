"""Shared helpers: where the files are, a DuckDB connection, and an order book replay.

By default every example reads the free one-day sample on Hugging Face in place:
https://huggingface.co/datasets/KalshiEye/kalshi-order-book-sample

To read files you downloaded instead, point KALSHIEYE_DATA at your kalshieye-data folder:
    export KALSHIEYE_DATA=/path/to/kalshieye-data
"""

from __future__ import annotations

import os

import duckdb

DATA = os.environ.get("KALSHIEYE_DATA", "hf://datasets/KalshiEye/kalshi-order-book-sample/kalshieye-data").rstrip("/")

# Datasets with one file per day; the others have one file per series (spot: per asset) per day.
DAILY = {"markets", "series", "settlements", "incidents"}


def files(dataset: str, series: str = "*") -> str:
    """A glob for one dataset's files, optionally for one series (or one spot asset)."""
    if dataset in DAILY:
        return f"{DATA}/{dataset}/*/*.parquet"
    if dataset == "spot":
        return f"{DATA}/spot/*/asset={series}/*.parquet"
    return f"{DATA}/{dataset}/*/series={series}/*.parquet"


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


class Book:
    """One market's order book, rebuilt from book_l2 rows applied in order.

    Kalshi books are bids only: a NO bid at p is an offer to sell YES at 1 - p,
    so the YES asks come from the NO side.
    """

    def __init__(self) -> None:
        self.yes: dict[float, float] = {}
        self.no: dict[float, float] = {}
        self._snapshot_ts = None

    def apply(self, ts, is_snapshot: bool, side: str | None, price: float | None, size: float | None) -> None:
        book = self.yes if side == "yes" else self.no
        if is_snapshot:
            # A snapshot replaces the whole book; its rows share one ts_recv.
            # A snapshot of an empty book is one row with no price.
            if ts != self._snapshot_ts:
                self.yes.clear()
                self.no.clear()
                self._snapshot_ts = ts
            if price is not None and size:
                book[price] = size
            return
        self._snapshot_ts = None
        if price is None or size is None:
            return
        # A delta is the signed change in size. Sizes are fractional, so round away float residue.
        left = round(book.get(price, 0.0) + size, 6)
        if left > 0:
            book[price] = left
        else:
            book.pop(price, None)

    def bids(self, levels: int = 5) -> list[tuple[float, float]]:
        return sorted(self.yes.items(), reverse=True)[:levels]

    def asks(self, levels: int = 5) -> list[tuple[float, float]]:
        return [(round(1 - p, 4), s) for p, s in sorted(self.no.items(), reverse=True)[:levels]]
