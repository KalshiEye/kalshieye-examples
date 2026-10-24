"""Calibration: do contracts priced at p win about p of the time?

For every settled market in the sample, take the YES mid of the last minute bar that
ended 5 minutes before close, group by price, and compare with how often YES won.
Writes calibration.png.
"""

import matplotlib.pyplot as plt

from kalshieye_sample import connect, files

con = connect()

rows = con.execute(f"""
    WITH settled AS (
      SELECT ticker, settlement_value, close_ts::TIMESTAMPTZ AS close_ts
      FROM '{files("settlements")}'
      WHERE result IN ('yes', 'no')
    ),
    last_mid AS (
      SELECT b.ticker, b.mid_close AS mid, s.settlement_value
      FROM '{files("bbo_1m")}' b JOIN settled s USING (ticker)
      WHERE b.minute::TIMESTAMPTZ + INTERVAL 1 MINUTE <= s.close_ts - INTERVAL 5 MINUTE
        AND b.mid_close IS NOT NULL
      QUALIFY row_number() OVER (PARTITION BY b.ticker ORDER BY b.minute DESC) = 1
    )
    SELECT least(floor(mid * 10), 9) / 10 + 0.05 AS bucket,
           count(*) AS markets,
           avg(mid) AS avg_price,
           avg(settlement_value) AS yes_rate
    FROM last_mid
    GROUP BY bucket
    ORDER BY bucket
""").fetchall()

print(f"{'price':>6} {'markets':>8} {'avg price':>10} {'YES won':>8}")
for bucket, n, price, won in rows:
    print(f"{bucket:6.2f} {n:8d} {price:10.3f} {won:8.3f}")

prices = [r[2] for r in rows]
plt.figure(figsize=(5, 5))
plt.plot([0, 1], [0, 1], color="#999999", linewidth=1, label="perfectly calibrated")
plt.scatter(prices, [r[3] for r in rows], s=[max(12, r[1] / 2) for r in rows], color="#d93b00", label="markets, by price")
plt.xlabel("YES mid 5 minutes before close")
plt.ylabel("Share that settled YES")
plt.title("Kalshi calibration, one day of sample markets")
plt.legend(loc="upper left")
plt.tight_layout()
plt.savefig("calibration.png", dpi=150)
print("\nwrote calibration.png")
