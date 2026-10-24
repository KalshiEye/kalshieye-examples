"""How wide is the spread, and how much is offered at the best prices, hour by hour (UTC)?

Each bbo row is the top of the book until the next row for the same market, so the
averages are weighted by how long each quote stood. Hours the recorder did not see in
full are left out: a quote carried through a gap is not a quote anyone could trade.
"""

from kalshieye_sample import connect, files

SERIES = "KXBTC15M"

con = connect()

print(con.sql(f"""
    WITH q AS (
      SELECT ticker, ts_recv::TIMESTAMPTZ AS ts, yes_bid, yes_ask, yes_bid_size, yes_ask_size,
             epoch(lead(ts_recv::TIMESTAMPTZ) OVER (PARTITION BY ticker ORDER BY ts_recv) - ts_recv::TIMESTAMPTZ) AS s
      FROM '{files("bbo", SERIES)}'
    ),
    gaps AS (
      SELECT hour_start::TIMESTAMPTZ AS hour_start
      FROM '{files("incidents")}'
      WHERE coverage_pct < 100
    )
    SELECT date_trunc('hour', ts) AS hour_utc,
           round(sum((yes_ask - yes_bid) * s) / sum(s) * 100, 2) AS spread_cents,
           round(sum(yes_bid_size * s) / sum(s)) AS bid_size,
           round(sum(yes_ask_size * s) / sum(s)) AS ask_size,
           count(*) AS quote_changes
    FROM q
    WHERE yes_bid IS NOT NULL AND yes_ask IS NOT NULL AND s > 0  -- both sides quoted
      AND date_trunc('hour', ts) NOT IN (SELECT hour_start FROM gaps)
    GROUP BY hour_utc
    ORDER BY hour_utc
""").df().to_string(index=False))
