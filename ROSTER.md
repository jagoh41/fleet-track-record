# The roster

24 systems, running on one live OANDA account. There is no second account, no
paper sleeve, and nothing excluded from the record.

**The table itself lives in [`data/roster.json`](data/roster.json)** — one source,
rendered on [the page](https://USERNAME.github.io/REPO/) and machine-readable here.
It carries, for every system: name, instrument, a plain-English mechanism, and the
live risk cap.

Pulled from `systemctl list-units 'tradebot_*' --state=active` on the trading host.
The **risk cap** is the live figure each service actually runs with, read from its
own launch arguments or config file — not from a planning spreadsheet. It is the
fraction of account equity risked between entry and stop on a single position.

## Notes that matter

**MR UK100 runs at a 0% cap.** It is live, it evaluates signals, and it will not
size a position. It is listed because it is running, not because it trades.

**Eight systems share NAS100, and the index sleeve can crowd out the rest.** The
NAS100 systems net into a single broker position, so the account's realised P&L on
that instrument is not the sum of eight independent strategies. More importantly,
the index systems together can use most of the account's margin during the US
session, and orders that arrive after that point — usually the metals systems —
are refused by the broker. `margin_refusals` in `data/summary.json` counts those
refusals inside the record window.

**Gold Trend TSMOM has no fixed risk cap.** It sizes to an 8% annualised volatility
target and only trades above £1,000 NAV, so it is not comparable to the per-trade
percentages on the other rows.

**Caps are per-position, not per-account.** With 24 systems live, simultaneous
positions can and do stack. There is no global risk governor beyond broker margin.

## Roster changes since the record opened

The record starts 2026-09-06 with the 24 systems listed in
[`data/roster.json`](data/roster.json). No system has been added, removed or
re-capped since — the `changes` array there is empty, and it stays the single
place a change is recorded.

Any future roster change gets a dated entry in `roster.json`, in the commit that
makes it. That is the whole point of publishing the roster.
