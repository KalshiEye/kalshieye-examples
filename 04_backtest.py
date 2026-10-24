"""Backtest: buy YES at the ask five minutes before close, in every 15-minute crypto market.

The walkthrough is at https://kalshieye.com/guides/backtest-kalshi-markets/
One day is far too few markets to judge a rule: this shows the mechanics.
"""

from kalshieye_sample import connect, files

con = connect()

for series in ["KXBTC15M", "KXETH15M"]:
    print(series)
    print(con.sql(f"""
        -- ::TIMESTAMPTZ lets every DuckDB version do interval math on the nanosecond timestamps.
        WITH settled AS (
          SELECT ticker, settlement_value, close_ts::TIMESTAMPTZ AS close_ts
          FROM '{files("settlements")}'
          WHERE series = '{series}' AND result IN ('yes', 'no')
        ),
        bars AS (
          SELECT ticker, minute::TIMESTAMPTZ AS minute, yes_ask_close
          FROM '{files("bbo_1m", series)}'
        ),
        gaps AS (
          -- Hours the recorder did not see in full.
          SELECT hour_start::TIMESTAMPTZ AS hour_start
          FROM '{files("incidents")}'
          WHERE coverage_pct < 100
        ),
        entries AS (
          -- Each market's last minute bar that had ended 5 minutes before close.
          SELECT b.ticker, b.minute, b.yes_ask_close AS ask, s.settlement_value
          FROM bars b JOIN settled s USING (ticker)
          WHERE b.minute + INTERVAL 1 MINUTE <= s.close_ts - INTERVAL 5 MINUTE
          QUALIFY row_number() OVER (PARTITION BY b.ticker ORDER BY b.minute DESC) = 1
        )
        SELECT
          floor(ask * 10) / 10 AS bucket,
          count(*) AS markets,
          round(avg(ask), 3) AS avg_ask,
          round(avg(settlement_value), 3) AS yes_rate,
          round(avg(settlement_value - ask - 0.07 * ask * (1 - ask)), 4) AS pnl_per_contract
        FROM entries
        WHERE ask IS NOT NULL
          AND date_trunc('hour', minute) NOT IN (SELECT hour_start FROM gaps)
        GROUP BY bucket
        ORDER BY bucket
    """).df().to_string(index=False))
    print()
