#!/usr/bin/env python3
"""Refresh the public track record from the broker.

READ-ONLY. This script issues GET requests only: it can never place, modify or
close a trade. Credentials are read from the environment (or from a file OUTSIDE
this repo via --env-file) and are never written to any output.

Usage:
    python update.py --env-file ../m1spy/.env
    OANDA_API_KEY=... OANDA_ACCOUNT_ID=... python update.py
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# The public record starts here. Fixed at publication; never moves.
START = dt.datetime(2026, 9, 6, 0, 0, tzinfo=dt.timezone.utc)
# The record tracks exactly one broker account, pinned here so the data can
# never silently follow a config change. This is an account id, not a credential.
ACCOUNT = "001-004-19806960-002"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SQ = chr(39)   # single quote, kept out of literals so this file stays shell-safe
DQ = chr(34)


def load_env(path=None):
    env = dict(os.environ)
    if path:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip().strip(DQ).strip(SQ))
        # mirror the live/practice prefix convention of the trading stack
        mode = env.get("OANDA_ENV", "live").lower()
        pref = "OANDA_PRACTICE_" if mode == "practice" else "OANDA_LIVE_"
        if env.get(pref + "API_KEY"):
            env["OANDA_API_KEY"] = env[pref + "API_KEY"]
        if env.get(pref + "ACCOUNT_ID"):
            env["OANDA_ACCOUNT_ID"] = env[pref + "ACCOUNT_ID"]
    return env


def ts(s):
    """Parse an OANDA RFC3339 stamp (nanosecond precision) to an aware datetime."""
    s = (s or "").rstrip("Z")
    if "." in s:
        a, b = s.split(".", 1)
        s = a + "." + b[:6]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)


class Broker:
    """Read-only OANDA client. Every method here is a GET."""

    def __init__(self, env):
        mode = env.get("OANDA_ENV", "live").lower()
        self.base = ("https://api-fxpractice.oanda.com" if mode == "practice"
                     else "https://api-fxtrade.oanda.com")
        self.key = env["OANDA_API_KEY"]
        self.acct = ACCOUNT

    def get(self, path, params=None):
        url = self.base + path + ("?" + urlencode(params, doseq=True) if params else "")
        req = Request(url, headers={"Authorization": "Bearer " + self.key})
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def summary(self):
        return self.get("/v3/accounts/%s/summary" % self.acct)["account"]

    def transactions(self, frm, to):
        d = self.get("/v3/accounts/%s/transactions" % self.acct,
                     {"from": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "to": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "pageSize": 1000})
        out = []
        for pg in d.get("pages", []):
            out.extend(self.get(pg.replace(self.base, "")).get("transactions", []))
        return out

    def closed_trades(self, since):
        rows, before = [], None
        while True:
            p = {"state": "CLOSED", "count": 500}
            if before:
                p["beforeID"] = before
            tr = self.get("/v3/accounts/%s/trades" % self.acct, p).get("trades", [])
            if not tr:
                break
            reached = False
            for t in tr:
                if not t.get("closeTime"):
                    continue
                if ts(t["closeTime"]) < since:
                    reached = True
                    continue
                rows.append(t)
            before = str(int(tr[-1]["id"]))
            if reached or len(tr) < 500:
                break
        return rows

    def open_trades(self):
        return self.get("/v3/accounts/%s/openTrades" % self.acct).get("trades", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", help="path to a .env OUTSIDE this repo")
    args = ap.parse_args()
    env = load_env(args.env_file)
    if not env.get("OANDA_API_KEY"):
        sys.exit("missing OANDA_API_KEY")

    broker = Broker(env)
    now = dt.datetime.now(dt.timezone.utc)
    acct = broker.summary()
    ccy = acct.get("currency", "GBP")
    lc = ccy.lower()

    # ---- closed trades ----
    def bot_tag(t):
        # The broker shows tag "0" (with an id/comment) on trades from several
        # different systems: a shared bookkeeping stamp, not a bot identity.
        # Report it as untagged so the tagged count means what it says.
        tag = (t.get("clientExtensions") or {}).get("tag", "")
        return "" if tag in ("", "0") else tag

    trades = sorted(broker.closed_trades(START), key=lambda t: ts(t["closeTime"]))
    rows = []
    for t in trades:
        units = float(t.get("initialUnits", 0))
        rows.append({
            "close_time": t["closeTime"][:19] + "Z",
            "open_time": (t.get("openTime") or "")[:19] + "Z",
            "instrument": t.get("instrument", ""),
            "direction": "long" if units > 0 else "short",
            "units": ("%.4f" % abs(units)).rstrip("0").rstrip("."),
            "entry_price": t.get("price", ""),
            "exit_price": t.get("averageClosePrice", ""),
            "realised_pl_" + lc: "%.2f" % float(t.get("realizedPL", 0)),
            "financing_" + lc: "%.4f" % float(t.get("financing", 0)),
            "broker_trade_id": t.get("id", ""),
            "bot_tag": bot_tag(t),
        })
    os.makedirs(DATA, exist_ok=True)
    # Always rewrite, even with zero rows: a stale file from a previous run must
    # never survive into a record that reports a different trade count.
    fields = ["close_time", "open_time", "instrument", "direction", "units",
              "entry_price", "exit_price", "realised_pl_" + lc, "financing_" + lc,
              "broker_trade_id", "bot_tag"]
    with open(os.path.join(DATA, "closed_trades.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # ---- balance series, straight off the broker own stamps ----
    txns = broker.transactions(START - dt.timedelta(days=21), now)
    opening = None
    series, flows = [], []
    margin_refusals = 0
    for t in txns:
        bal = t.get("accountBalance")
        when = ts(t.get("time"))
        if bal is not None:
            if when < START:
                opening = float(bal)          # last balance before the record opens
            else:
                series.append({"time": t["time"][:19] + "Z",
                               "balance": round(float(bal), 2)})
        if t.get("type") == "TRANSFER_FUNDS":
            flows.append({"time": t["time"][:19] + "Z",
                          "amount": float(t.get("amount", 0)),
                          "reason": t.get("fundingReason", ""),
                          "in_window": when >= START})
        # An order the broker refused for margin never becomes a trade, so the
        # trade list cannot show it. Count them so the crowding-out is measurable.
        if (t.get("type") == "ORDER_CANCEL" and t.get("reason") == "INSUFFICIENT_MARGIN"
                and when >= START):
            margin_refusals += 1
    if opening is None:
        opening = (float(acct.get("balance", 0))
                   - sum(float(t.get("realizedPL", 0)) for t in trades))
    series.insert(0, {"time": START.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "balance": round(opening, 2)})
    with open(os.path.join(DATA, "equity.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["time", "balance"], lineterminator="\n")
        w.writeheader()
        w.writerows(series)

    # ---- summary ----
    pls = [float(t.get("realizedPL", 0)) for t in trades]
    # Capital flows INSIDE the window are money moving, never performance. Subtract them from the NAV-based return so a
    # withdrawal cannot be published as a loss (2026-09-09: -250.00 was reading as -12 % of the account).
    net_flows = round(sum(f["amount"] for f in flows if f["in_window"]), 2)
    capital_contributed = round(opening + net_flows, 2)
    wins = [p for p in pls if p > 0]
    losses = [p for p in pls if p < 0]
    opens = broker.open_trades()
    nav = float(acct.get("NAV", 0))
    summary = {
        "record_start": START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "currency": ccy,
        "opening_balance": round(opening, 2),
        "balance": round(float(acct.get("balance", 0)), 2),
        "nav": round(nav, 2),
        "unrealised_pl": round(float(acct.get("unrealizedPL", 0)), 2),
        "realised_pl": round(sum(pls), 2),
        "financing": round(sum(float(t.get("financing", 0)) for t in trades), 2),
        "closed_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100.0 * len(wins) / len(pls), 1) if pls else None,
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else None,
        "largest_win": round(max(pls), 2) if pls else 0.0,
        "largest_loss": round(min(pls), 2) if pls else 0.0,
        "open_trades": len(opens),
        "open_unrealised": round(sum(float(t.get("unrealizedPL", 0)) for t in opens), 2),
        "tagged_trades": sum(1 for r in rows if r["bot_tag"]),
        # Deposits/withdrawals INSIDE the window would distort any return figure.
        # The record covers this window only; nothing outside it is published.
        "capital_flows_in_window": [f for f in flows if f["in_window"]],
        "net_capital_flows_in_window": net_flows,
        "capital_contributed": capital_contributed,
        "margin_refusals": margin_refusals,
        "realised_return_pct_on_opening": (round(100.0 * sum(pls) / opening, 2)
                                           if opening else None),
        # NAV return with capital flows removed: what the trading did, not what the bank transfer did.
        "nav_return_pct_on_opening": (round(100.0 * (nav - opening - net_flows) / opening, 2)
                                      if opening else None),
        "nav_return_pct_on_capital": (round(100.0 * (nav - capital_contributed) / capital_contributed, 2)
                                      if capital_contributed else None),
    }
    with open(os.path.join(DATA, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    print(json.dumps(summary, indent=2))
    print("\nwrote %d trades, %d balance points to %s" % (len(rows), len(series), DATA))
    n_in = len(summary["capital_flows_in_window"])
    if n_in:
        print("!! %d capital flow(s) INSIDE the window - these MUST be disclosed" % n_in)


if __name__ == "__main__":
    main()
