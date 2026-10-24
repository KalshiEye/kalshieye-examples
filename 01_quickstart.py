"""Quick start: the day's busiest NFL markets, from the trades and markets files."""

from kalshieye_sample import connect, files

con = connect()

print(con.sql(f"""
    WITH t AS (
      SELECT ticker,
             count(*) AS trades,
             sum(size) AS contracts,
             sum(yes_price * size) / sum(size) AS vwap,
             arg_min(yes_price, ts_recv) AS first_price,
             arg_max(yes_price, ts_recv) AS last_price
      FROM '{files("trades", "KXNFLGAME")}'
      GROUP BY ticker
    ),
    m AS (
      -- The markets file lists every market open that day, with what YES means.
      SELECT ticker, any_value(yes_sub_title) AS yes_means
      FROM '{files("markets")}'
      WHERE series = 'KXNFLGAME'
      GROUP BY ticker
    )
    SELECT t.ticker, m.yes_means, t.trades, round(t.contracts) AS contracts,
           round(t.vwap, 3) AS vwap, t.first_price, t.last_price
    FROM t LEFT JOIN m USING (ticker)
    ORDER BY contracts DESC
    LIMIT 10
""").df().to_string(index=False))
