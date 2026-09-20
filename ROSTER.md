# The roster

33 systems, running on one live OANDA account — 24 sized, nine at a 0% cap. There
is no second account, no paper sleeve, and nothing excluded from the record. The headline count on the
page is read from the roster file, never typed in.

**The table itself lives in [`data/roster.json`](data/roster.json)** — one source,
rendered on [the page](https://jagoh41.github.io/fleet-track-record/) and machine-readable here.
It carries, for every system: name, instrument, a plain-English mechanism, and the
live risk cap.

Pulled from `systemctl list-units 'tradebot_*' --state=active` on the trading host.
The **risk cap** is the live figure each service actually runs with, read from its
own launch arguments or config file — not from a planning spreadsheet. It is the
fraction of account equity risked between entry and stop on a single position.

## Notes that matter

**Several systems run at a 0% cap.** They are live, they evaluate signals, and
they will not size a position; they are listed because they are running, not
because they trade. Their rows are muted on the page and the roster marks each
one. A cap is set to zero when the fleet's sizing rules give a system no budget;
the service keeps running so its forward record keeps accruing.

**Nine systems share NAS100 (eight of their own plus a VRP leg), and the index
sleeve can crowd out the rest.** The NAS100 systems net into a single broker
position, so the account's realised P&L on that instrument is not the sum of
nine independent strategies. More importantly,
the index systems together can use most of the account's margin during the US
session, and orders that arrive after that point — usually the metals systems —
are refused by the broker. `margin_refusals` in `data/summary.json` counts those
refusals inside the record window.

**Gold Trend TSMOM has no fixed risk cap.** It sizes to an 8% annualised volatility
target and only trades above £1,000 NAV, so it is not comparable to the per-trade
percentages on the other rows.

**Caps are per-position, not per-account.** With 33 systems live, simultaneous
positions can and do stack. There is no global risk governor beyond broker margin.

## Roster changes since the record opened

The record started 2026-09-06 with 24 systems. Every addition, removal and
re-cap since is a dated entry in the `changes` array of
[`data/roster.json`](data/roster.json), which is the single place a change is
recorded; the page renders that array beneath the roster table. In short: a gold
short-side fade was added on 2026-09-07, a metals book (crosses and copper) on
2026-09-12, the US30 event scalper was stopped on 2026-09-13, and the risk caps
were re-sized on 2026-09-13, 2026-09-16 and 2026-09-17 to vectors chosen by the
fleet's sizing process. On 2026-09-16 every system's rule-building process was
re-run walk-forward (fit through year Y, trade year Y+1 blind); several hand-tuned
systems produced no honest record that way and were set to 0%, and from
2026-09-17 the caps are sized on the walk-forward records rather than on each
system's own tuning history. Six systems built the same way were added on
2026-09-18 (momentum continuation on Brent, DE30, NAS100 and USD/JPY, a USD/JPY
channel breakout, a US30 Donchian breakout), a NAS100 volume-climax system on
2026-09-19 and an HK33 cash-session short on 2026-09-20. On 2026-09-20 the caps
were re-cut twice and three of the new momentum systems (DE30, NAS100, USD/JPY)
were set to 0% after their 2026 stretch failed the fleet's own tests. Nine
systems now run at 0%.

Any future roster change gets a dated entry in `roster.json`, in the commit that
makes it. That is the whole point of publishing the roster.
