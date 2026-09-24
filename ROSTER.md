# The roster

23 systems, running on one live OANDA account, every one of them sized. There
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

**No system runs at a 0% cap any more.** Until 2026-09-24 nine did: they were live
and evaluated signals but never sized a position, because the fleet's sizing rules
gave them no budget. They were switched off that day and left the roster; their
rows survive in the dated `changes` log. If a system is ever set to 0% again, its
row is muted on the page.

**Six systems share NAS100 (five of their own plus a VRP leg), and the index
sleeve can crowd out the rest.** The NAS100 systems net into a single broker
position, so the account's realised P&L on that instrument is not the sum of
six independent strategies; a system whose signal points the other way from a
position another system already holds is skipped rather than netted against it. More importantly,
the index systems together can use most of the account's margin during the US
session, and orders that arrive after that point — usually the metals systems —
are refused by the broker. `margin_refusals` in `data/summary.json` counts those
refusals inside the record window.

**Gold Trend TSMOM has no fixed risk cap.** It sizes to an 8% annualised volatility
target and only trades above £1,000 NAV, so it is not comparable to the per-trade
percentages on the other rows.

**Caps are per-position, not per-account.** With 23 systems live, simultaneous
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
were set to 0% after their 2026 stretch failed the fleet's own tests.

On 2026-09-23 at 23:03 UTC six systems built by moving proven rules to new
instruments were deployed (an opening-range system on SPX500, an opening-drive
system on NAS100, channel breakouts on DE30 and on JP225 with a closer target, a
volatility breakout on gold in sterling and a rolling channel on the Swiss index),
and the NAS100 opening-range system's cap was raised from 0.85% to 6%. At 23:27 UTC,
24 minutes later, four of the six were switched off when their 2026 records to date
failed a check registered before deployment; none of them had traded. The NAS100
opening-range cap went back to 0.85% at 00:10 UTC. On 2026-09-24 the caps were
re-sized at 09:24 UTC; the nine systems at 0% were switched off at 10:47; the NAS100
opening-range system (its record after its tuning period was flat) and the HK33 cash
short (it did not hedge the fleet's losing days) at 11:21; the NAS100 volume-climax
system (a change in the broker's data feed had stopped it firing since May) at 11:28;
and the caps were re-sized again at 12:08. The roster now holds 23 systems, all sized.

Any future roster change gets a dated entry in `roster.json`, in the commit that
makes it. That is the whole point of publishing the roster.
