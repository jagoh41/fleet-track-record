#!/usr/bin/env python3
"""Pull the public track record from OANDA.

Only GET requests, so it can't place, change or close a trade. The API key comes
from the environment or from an env file kept outside this repo, and is never
written to any output.

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

# Start of the public record. Fixed when the record was published.
START = dt.datetime(2026, 9, 6, 0, 0, tzinfo=dt.timezone.utc)
# The one account the record follows, hard-coded so a config change can't move it.
ACCOUNT = "001-004-19806960-002"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load_env(path=None):
    env = dict(os.environ)
    if path:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        # the trading code keeps live and practice keys under different prefixes
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
    """Minimal OANDA v20 client. Every method is a GET."""

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

    # closed trades
    def bot_tag(t):
        # OANDA shows tag "0" on trades from several different systems, so "0"
        # doesn't identify anything. Treat it as untagged.
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
    # Rewrite the file even when there are no rows, so an old one can't linger.
    fields = ["close_time", "open_time", "instrument", "direction", "units",
              "entry_price", "exit_price", "realised_pl_" + lc, "financing_" + lc,
              "broker_trade_id", "bot_tag"]
    with open(os.path.join(DATA, "closed_trades.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # balance after each transaction, as OANDA reports it
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
        # Orders refused for lack of margin never become trades, so count them here.
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

    # summary
    pls = [float(t.get("realizedPL", 0)) for t in trades]
    # Deposits and withdrawals aren't trading results, so they're taken out of the returns.
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
        "capital_flows_in_window": [f for f in flows if f["in_window"]],
        "net_capital_flows_in_window": net_flows,
        "capital_contributed": capital_contributed,
        "margin_refusals": margin_refusals,
        "realised_return_pct_on_opening": (round(100.0 * sum(pls) / opening, 2)
                                           if opening else None),
        "nav_return_pct_on_opening": (round(100.0 * (nav - opening - net_flows) / opening, 2)
                                      if opening else None),
        "nav_return_pct_on_capital": (round(100.0 * (nav - capital_contributed) / capital_contributed, 2)
                                      if capital_contributed else None),
    }
    with open(os.path.join(DATA, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    # account value (NAV), one row per UTC hour: the latest reading replaces the
    # current hour's row, and an unchanged value writes nothing
    nav_path = os.path.join(DATA, "nav.csv")
    navs = []
    if os.path.exists(nav_path):
        with open(nav_path, encoding="utf-8") as f:
            navs = [(r["time"], r["nav"]) for r in csv.DictReader(f)]
    stamp, value = now.strftime("%Y-%m-%dT%H:%M:%SZ"), "%.2f" % nav
    if not navs or navs[-1][1] != value:
        if navs and navs[-1][0][:13] == stamp[:13]:
            navs[-1] = (stamp, value)
        else:
            navs.append((stamp, value))
        with open(nav_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["time", "nav"])
            w.writerows(navs)

    print("%d closed trades, %d balance points, balance %.2f, NAV %.2f, %d open"
          % (len(rows), len(series), summary["balance"], summary["nav"], len(opens)))


if __name__ == "__main__":
    main()
