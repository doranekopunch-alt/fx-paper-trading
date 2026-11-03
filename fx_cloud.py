#!/usr/bin/env python3
"""FX paper-trading daily snapshot. No brokerage access, no real orders."""
import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
import yfinance as yf

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
PAIRS = {"USDJPY": ("JPY=X", .01), "EURJPY": ("EURJPY=X", .01), "EURUSD": ("EURUSD=X", .0001)}
INITIAL = 10000.0
SPREAD_PIPS = 2.0
# Equal notional allocation; 1x unleveraged paper exposure, no interest/swap/taxes.
def load_state():
    path = DATA / "state.json"
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if "last_date" in state and "balances" in state:
            return state
    return {"last_date": {}, "balances": {p: INITIAL / 3 for p in PAIRS}, "history": []}

def analyze(ticker, pip):
    raw = yf.download(ticker, period="2y", interval="1d", auto_adjust=True,
                      progress=False, threads=False)
    if raw.empty:
        raise RuntimeError("価格データなし")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").dropna().sort_index()
    close.index = pd.to_datetime(close.index)
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close = close[~close.index.duplicated(keep="last")]
    close = close[close.index.date < datetime.now(JST).date()]
    if len(close) < 100:
        raise RuntimeError("価格データ不足")
    s20, s60 = close.rolling(20).mean(), close.rolling(60).mean()
    signal = pd.Series(0, index=close.index)
    signal.loc[(s20 > s60) & s60.notna()] = 1
    signal.loc[(s20 < s60) & s60.notna()] = -1
    # Signal from previous close governs the next close-to-close return.
    pos = signal.shift(1).fillna(0)
    ret = close.pct_change().fillna(0)
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * SPREAD_PIPS * pip / close.shift(1).fillna(close)
    daily_net = pos * ret - cost
    return close, signal, daily_net

def main():
    DATA.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    state = load_state()
    report = {"generated_at": datetime.now(JST).isoformat(), "pairs": {}, "warnings": [],
              "currency": "JPY", "initial_jpy": INITIAL}
    # State is only advanced for complete new price dates; retries never duplicate days.
    for name, (ticker, pip) in PAIRS.items():
        try:
            close, signal, daily_net = analyze(ticker, pip)
            last = state["last_date"].get(name)
            # First run starts at latest available close, not retroactively pretending live trades.
            if not last:
                state["last_date"][name] = str(close.index[-1].date())
                state["history"].append({"pair": name, "date": state["last_date"][name],
                                         "balance_jpy": round(state["balances"][name], 2),
                                         "note": "開始日・売買損益は未計上"})
            else:
                new = daily_net.loc[[str(d.date()) > last for d in daily_net.index]]
                for date, value in new.items():
                    day = str(date.date())
                    factor = 1 + float(value)
                    if not math.isfinite(factor) or factor <= 0:
                        raise RuntimeError("異常な損益率")
                    state["balances"][name] *= factor
                    state["last_date"][name] = day
                    state["history"].append({"pair": name, "date": day,
                                             "balance_jpy": round(state["balances"][name], 2),
                                             "daily_return_pct": round(float(value) * 100, 4)})
            sig = int(signal.iloc[-1])
            report["pairs"][name] = {
                "date": str(close.index[-1].date()),
                "signal": {1:"買い", -1:"売り", 0:"待機"}[sig],
                "balance_jpy": round(state["balances"][name], 2),
                "close": round(float(close.iloc[-1]), 5),
            }
        except Exception as exc:
            report["warnings"].append(f"{name}: {type(exc).__name__}: {exc}")
            report["pairs"][name] = {"error": "更新失敗", "balance_jpy": round(state["balances"][name], 2)}
    report["total_jpy"] = round(sum(state["balances"].values()), 2)
    report["pnl_jpy"] = round(report["total_jpy"] - INITIAL, 2)
    report["history"] = state["history"][-180:]
    (DATA / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": report["total_jpy"], "warnings": report["warnings"]}, ensure_ascii=False))
    if len(report["warnings"]) == len(PAIRS):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
