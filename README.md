# Live fleet track record

A public, append-only record of 24 automated trading systems running on one live
OANDA account.

**The record opens 2026-08-30 and never moves.** Every closed trade from that
moment on appears here, win or lose, with no bot excluded and no window
re-chosen. The roster is published in [`ROSTER.md`](ROSTER.md) with the live risk
cap each system actually runs.

📈 **[View the record →](https://USERNAME.github.io/REPO/)**

---

## Read this before you read the numbers

**This record is days old, not years old.** Nothing here is statistically
meaningful yet. A profit factor computed on twenty trades is a description of
twenty trades, not evidence of an edge.

**The account is small — roughly £1,250 at the open.** Percentage returns on an
account this size swing violently and do not transfer to a larger one. The £
column is the honest one; the % column is arithmetic.

**The first days are backfilled.** The record starts 2026-08-30, but the page was
published several days later, which means the opening stretch was already known
when it went up. That segment is marked **backfilled** on the chart and in the
data. Only trades after the publication marker were unknown at the moment of
publishing. If the backfilled head looks good, that is precisely why you should
discount it — treat it as a claim about the past and judge the forward segment
instead.

**Nine or so positions are usually open.** Unrealised P&L is reported separately
from realised and can reverse entirely. Any figure that blends the two is marked
as doing so.

## How to verify it

The point of a track record is that you do not have to take the author's word for
it, so there are three independent layers:

1. **Broker verification** — *(link pending)* a third-party read-only view of the
   account, published by the broker-verification service rather than by me.
2. **The raw data** — [`data/closed_trades.csv`](data/closed_trades.csv) is every
   closed trade with broker trade IDs, entry and exit prices, and realised P&L.
   [`data/equity.csv`](data/equity.csv) is the account balance stamped by the
   broker after each transaction, not reconstructed by me.
3. **The commit history** — this repository is append-only. Each refresh is a
   commit with a timestamp. If a losing day were ever quietly removed, the diff
   would show it. Read the history, not just the current state.

## What is published, and what is not

**Published:** every closed trade, the account balance series, the full roster,
each system's instrument, its live risk cap, and a plain-English description of
its mechanism.

**Not published:** strategy parameters, entry and exit logic, and source code. The
descriptions in [`ROSTER.md`](ROSTER.md) say what family each system belongs to and
what it trades — enough to judge whether the roster is diversified or whether eight
systems are quietly making the same bet, which is the question that actually
matters.

## Known weaknesses

Listed here because a track record that only publishes its strengths is marketing.

- **There is no per-bot P&L breakdown, and there cannot be one yet.** Most orders
  reach the broker without a bot tag, so the broker's own records cannot say which
  system placed which trade. Splitting the P&L 24 ways would mean falling back on
  self-reported logs, which is exactly the sort of unverifiable claim this record
  exists to avoid. Account-level figures are the only ones that are fully
  verifiable, so account-level is all that is reported. Per-bot attribution starts
  the day tagging ships, and not one day earlier.
- **Eight systems trade NAS100 and net into a single broker position.** The account
  result on that instrument is not the sum of eight independent strategies.
- **Live fills are not backtest fills.** Slippage and the netting above are paid in
  cash on this account. This record measures the live side of that, which is the
  side that pays.
- **The roster was pruned two days into the window.** Two systems were disabled on
  2026-09-02. Their trades before that point are included. See
  [`ROSTER.md`](ROSTER.md).

## Method

- **Source:** the OANDA v3 API, read-only. [`update.py`](update.py) issues GET
  requests only and cannot place, modify or close a trade.
- **Currency:** GBP, the account's own denomination. No conversion is applied.
- **Realised P&L** is the broker's `realizedPL` per closed trade. **Financing**
  (swap) is reported separately and is not netted into trade P&L.
- **The balance series** uses the broker's `accountBalance` stamp on each
  transaction. It is not reconstructed from trade P&L.
- **Deposits and withdrawals** inside the window are listed in
  [`data/summary.json`](data/summary.json) and annotated on the chart, because a
  transfer moves the balance without a trade. There were none at publication.
- **Refresh:** run `python update.py --env-file <path outside this repo>` and
  commit. Credentials are never read from, or written into, this repository.

## Disclaimer

This is a personal engineering project, published as a record of what these
systems actually did. It is not investment advice, not a solicitation, not an
offer to manage money, and not a signal service. Nothing here is a
recommendation to trade anything. Automated trading loses money for most people
who attempt it.
