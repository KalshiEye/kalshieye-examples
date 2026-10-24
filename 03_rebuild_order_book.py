"""Rebuild one market's full order book from book_l2, then check it against bbo.

book_l2 has every change to every price level. Replaying it gives the whole book at
any instant, and its best bid and ask must match the bbo file at the same moment.
"""

from itertools import zip_longest

from kalshieye_sample import Book, connect, files

TICKER = "KXNFLGAME-26OCT12BUFLAR-BUF"  # Bills vs Rams, Monday night: YES if Buffalo wins
AT = "2026-10-13 03:00:00+00"  # 11 PM Eastern, during the game, in an hour with full recording

con = connect()

rows = con.execute(
    f"""
    SELECT ts_recv, is_snapshot, side, price, size
    FROM '{files("book_l2", "KXNFLGAME")}'
    WHERE ticker = ? AND ts_recv::TIMESTAMPTZ <= ?::TIMESTAMPTZ
    ORDER BY ts_recv, seq
    """,
    [TICKER, AT],
).fetchall()

book = Book()
for ts, is_snapshot, side, price, size in rows:
    book.apply(ts, is_snapshot, side, price, size)

print(f"{TICKER} at {AT}, rebuilt from {len(rows):,} book_l2 rows\n")
print(f"{'YES bid':>8} {'size':>12}   {'YES ask':>8} {'size':>12}")
for (bp, bs), (ap, az) in zip_longest(book.bids(10), book.asks(10), fillvalue=(None, None)):
    left = f"{bp:8.2f} {bs:12,.2f}" if bp is not None else " " * 21
    right = f"{ap:8.2f} {az:12,.2f}" if ap is not None else ""
    print(f"{left}   {right}")

quote = con.execute(
    f"""
    SELECT yes_bid, yes_bid_size, yes_ask, yes_ask_size
    FROM '{files("bbo", "KXNFLGAME")}'
    WHERE ticker = ? AND ts_recv::TIMESTAMPTZ <= ?::TIMESTAMPTZ
    ORDER BY ts_recv DESC
    LIMIT 1
    """,
    [TICKER, AT],
).fetchone()

(best_bid, bid_size), (best_ask, ask_size) = book.bids(1)[0], book.asks(1)[0]
rebuilt = (best_bid, round(bid_size, 2), best_ask, round(ask_size, 2))
from_bbo = (quote[0], round(quote[1], 2), quote[2], round(quote[3], 2))
print(f"\nrebuilt top of book: {rebuilt}")
print(f"bbo file:            {from_bbo}")
print("match" if rebuilt == from_bbo else "MISMATCH")
