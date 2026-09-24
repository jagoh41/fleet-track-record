# Fleet track record

The live record of the automated trading systems I run on one OANDA account, in pounds. Every trade
closed since 6 September 2026 is in here.

Page: https://jagoh41.github.io/fleet-track-record/

Every 15 minutes the trading server reads the account from OANDA's API with `update.py` (GET requests
only) and commits anything that changed, so the history shows what the account looked like at each point.

## Files

- `data/closed_trades.csv`: every closed trade, with OANDA's trade ID
- `data/equity.csv`: the balance after each transaction, as OANDA reports it
- `data/nav.csv`: the account value including open positions, hourly (from the trading server's own log before 24 September)
- `data/summary.json`: headline numbers, transfers in and out, refused orders
- `data/roster.json`: the systems running now, their risk caps, and a dated log of changes
- `data/meta.json`: when the record starts and when it went public

## Notes

- The account (001-004-19806960-002) was funded with £2,000 on 4 September 2026 and had never traded.
  The record starts at 00:00 UTC on 6 September and went public at 13:25 UTC that day, before the first
  trade.
- £250 was withdrawn on 9 September and paid back on 17 September. Transfers are left out of the chart
  and the returns.
- The figures are for the whole account. Most orders reach OANDA without a system tag, so there's no
  reliable split by system.
- The systems share the account's margin. When the index systems are using most of it, OANDA turns down
  new orders, and those never become trades. `margin_refusals` in `summary.json` counts them.
- Systems get added, stopped and resized. Each change is logged in `roster.json` with its date.
- It's a few weeks of data on a small account, so it doesn't prove much yet.

[Myfxbook](https://www.myfxbook.com/members/jagoh41/live20from20september202026/12183574) also tracks
the account, but it hasn't updated since 9 September because of a fault on their side, which has been
reported.

Personal project, not investment advice.
