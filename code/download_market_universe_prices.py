from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "data"

SP100_WIKI = "https://en.wikipedia.org/wiki/S%26P_100"
NASDAQ100_WIKI = "https://en.wikipedia.org/wiki/Nasdaq-100"
NASDAQ100_NASDAQ = "https://www.nasdaq.com/solutions/global-indexes/nasdaq-100/companies"
TAIWAN50_REFERENCE = "https://www.yuantaetfs.com/product/detail/0050/Basic_information"


TAIWAN50_FALLBACK = [
    "1216",
    "1303",
    "2059",
    "2301",
    "2303",
    "2308",
    "2317",
    "2327",
    "2330",
    "2344",
    "2345",
    "2357",
    "2360",
    "2368",
    "2382",
    "2383",
    "2395",
    "2408",
    "2412",
    "2449",
    "2454",
    "2603",
    "2880",
    "2881",
    "2882",
    "2883",
    "2884",
    "2885",
    "2886",
    "2887",
    "2890",
    "2891",
    "2892",
    "3008",
    "3017",
    "3037",
    "3045",
    "3231",
    "3443",
    "3653",
    "3661",
    "3665",
    "3711",
    "4904",
    "4958",
    "5880",
    "6505",
    "6669",
    "7769",
    "8046",
]


TAIWAN50_FALLBACK_NAMES = {
    "1216": "Uni-President",
    "1303": "Nan Ya Plastics",
    "2059": "King Slide",
    "2301": "Lite-On Technology",
    "2303": "United Microelectronics",
    "2308": "Delta Electronics",
    "2317": "Hon Hai Precision",
    "2327": "Yageo",
    "2330": "Taiwan Semiconductor Manufacturing",
    "2344": "Winbond Electronics",
    "2345": "Accton Technology",
    "2357": "Asustek Computer",
    "2360": "Chroma ATE",
    "2368": "Gold Circuit Electronics",
    "2382": "Quanta Computer",
    "2383": "Elite Material",
    "2395": "Advantech",
    "2408": "Nanya Technology",
    "2412": "Chunghwa Telecom",
    "2449": "King Yuan Electronics",
    "2454": "MediaTek",
    "2603": "Evergreen Marine",
    "2880": "Hua Nan Financial",
    "2881": "Fubon Financial",
    "2882": "Cathay Financial",
    "2883": "KGI Financial",
    "2884": "E.SUN Financial",
    "2885": "Yuanta Financial",
    "2886": "Mega Financial",
    "2887": "Taishin Shin Kong Financial",
    "2890": "SinoPac Financial",
    "2891": "CTBC Financial",
    "2892": "First Financial",
    "3008": "Largan Precision",
    "3017": "Asia Vital Components",
    "3037": "Unimicron Technology",
    "3045": "Taiwan Mobile",
    "3231": "Wistron",
    "3443": "Global Unichip",
    "3653": "Jentech Precision",
    "3661": "Alchip Technologies",
    "3665": "BizLink Holding",
    "3711": "ASE Technology Holding",
    "4904": "Far EasTone",
    "4958": "Zhen Ding Technology Holding",
    "5880": "Taiwan Cooperative Financial",
    "6505": "Formosa Petrochemical",
    "6669": "Wiwynn",
    "7769": "Hong Jing",
    "8046": "Nan Ya Printed Circuit Board",
}


def normalize_us_ticker(value: object) -> str:
    ticker = str(value).strip().upper()
    ticker = re.sub(r"\s+", "", ticker)
    return ticker.replace(".", "-")


def normalize_tw_ticker(value: object) -> str | None:
    text = str(value).strip()
    match = re.search(r"\b(\d{4})\b", text)
    if not match:
        return None
    return f"{match.group(1)}.TW"


def fetch_wikipedia_tickers(url: str, preferred_columns: Iterable[str]) -> pd.DataFrame:
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    preferred = [c.lower() for c in preferred_columns]
    for table in tables:
        columns = {str(col).strip().lower(): col for col in table.columns}
        match = next((columns[col] for col in preferred if col in columns), None)
        if match is None:
            continue
        out = pd.DataFrame()
        out["ticker"] = table[match].map(normalize_us_ticker)
        name_col = next(
            (columns[c] for c in ["company", "security", "company name", "name"] if c in columns),
            None,
        )
        out["name"] = table[name_col].astype(str) if name_col is not None else ""
        out = out[out["ticker"].str.match(r"^[A-Z0-9-]+$", na=False)].drop_duplicates("ticker")
        if len(out) >= 90:
            return out.reset_index(drop=True)
    raise RuntimeError(f"Could not find ticker table in {url}")


def fetch_nasdaq100_tickers() -> pd.DataFrame:
    response = requests.get(
        NASDAQ100_NASDAQ,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    for table in tables:
        columns = {str(col).strip().lower(): col for col in table.columns}
        if "symbol" not in columns:
            if table.shape[1] >= 2 and str(table.iloc[0, 0]).strip().lower() == "symbol":
                table = table.iloc[1:].copy()
                table.columns = ["Symbol", "Company Name"] + [f"extra_{i}" for i in range(table.shape[1] - 2)]
                columns = {str(col).strip().lower(): col for col in table.columns}
            else:
                continue
        out = pd.DataFrame()
        out["ticker"] = table[columns["symbol"]].map(normalize_us_ticker)
        name_col = columns.get("company name")
        out["name"] = table[name_col].astype(str) if name_col is not None else ""
        out = out[out["ticker"].str.match(r"^[A-Z0-9-]+$", na=False)].drop_duplicates("ticker")
        if len(out) >= 90:
            return out.reset_index(drop=True)
    return fetch_wikipedia_tickers(NASDAQ100_WIKI, ["ticker", "symbol"])


def fetch_taiwan50_tickers() -> pd.DataFrame:
    return fallback_taiwan50()


def fallback_taiwan50() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"{code}.TW" for code in TAIWAN50_FALLBACK],
            "name": [TAIWAN50_FALLBACK_NAMES.get(code, "") for code in TAIWAN50_FALLBACK],
        }
    )


def load_universes(selected: list[str], allow_fallback: bool) -> pd.DataFrame:
    frames = []
    if "sp100" in selected:
        sp100 = fetch_wikipedia_tickers(SP100_WIKI, ["symbol", "ticker"])
        sp100["universe"] = "SP100"
        sp100["source"] = SP100_WIKI
        frames.append(sp100)
    if "nasdaq100" in selected:
        ndx = fetch_nasdaq100_tickers()
        ndx["universe"] = "NASDAQ100"
        ndx["source"] = NASDAQ100_NASDAQ
        frames.append(ndx)
    if "taiwan50" in selected:
        tw50 = fetch_taiwan50_tickers()
        tw50["source"] = TAIWAN50_REFERENCE
        tw50["universe"] = "TAIWAN50"
        frames.append(tw50)
    tickers = pd.concat(frames, ignore_index=True)
    return tickers[["universe", "ticker", "name", "source"]].drop_duplicates(["universe", "ticker"])


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def adjusted_close_from_download(downloaded: pd.DataFrame) -> pd.DataFrame:
    if downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        field = "Adj Close" if "Adj Close" in downloaded.columns.get_level_values(0) else "Close"
        prices = downloaded[field].copy()
    else:
        field = "Adj Close" if "Adj Close" in downloaded.columns else "Close"
        prices = downloaded[[field]].copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    return prices.sort_index()


def download_prices_for_universe(
    universe: str,
    tickers: list[str],
    start: str,
    end: str,
    batch_size: int,
    pause_sec: float,
) -> tuple[pd.DataFrame, list[dict]]:
    pieces = []
    errors = []
    for batch in chunks(tickers, batch_size):
        try:
            data = yf.download(
                tickers=batch,
                start=start,
                end=end,
                auto_adjust=False,
                actions=False,
                group_by="column",
                threads=True,
                progress=False,
            )
            prices = adjusted_close_from_download(data)
            if len(batch) == 1 and not prices.empty:
                prices.columns = batch
            pieces.append(prices)
        except Exception as exc:
            for ticker in batch:
                errors.append({"universe": universe, "ticker": ticker, "error": str(exc)})
        if pause_sec:
            time.sleep(pause_sec)
    if not pieces:
        return pd.DataFrame(), errors
    wide = pd.concat(pieces, axis=1)
    wide = wide.loc[:, ~wide.columns.duplicated()].sort_index()
    wide.columns = [str(col).upper() for col in wide.columns]
    return wide, errors


def quality_report(universe: str, wide: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    rows = []
    expected_days = max(len(wide), 1)
    for ticker in wide.columns:
        series = wide[ticker].dropna()
        rows.append(
            {
                "universe": universe,
                "ticker": ticker,
                "start_requested": start,
                "end_requested": end,
                "first_date": series.index.min().date().isoformat() if not series.empty else "",
                "last_date": series.index.max().date().isoformat() if not series.empty else "",
                "observations": int(series.shape[0]),
                "coverage": float(series.shape[0] / expected_days),
                "missing": int(expected_days - series.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def write_long_prices(universe: str, wide: pd.DataFrame, out_path: Path) -> None:
    if wide.empty:
        pd.DataFrame(columns=["date", "universe", "ticker", "adj_close"]).to_csv(
            out_path, index=False, encoding="utf-8-sig"
        )
        return
    long = (
        wide.reset_index(names="date")
        .melt(id_vars="date", var_name="ticker", value_name="adj_close")
        .dropna(subset=["adj_close"])
    )
    long.insert(1, "universe", universe)
    long.to_csv(out_path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download P1 market validation prices with yfinance.")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default=dt.date.today().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--universes",
        default="sp100,nasdaq100,taiwan50",
        help="Comma-separated: sp100,nasdaq100,taiwan50",
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--pause-sec", type=float, default=1.0)
    parser.add_argument("--min-coverage", type=float, default=0.80)
    parser.add_argument("--allow-taiwan50-fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = [part.strip().lower() for part in args.universes.split(",") if part.strip()]
    invalid = sorted(set(selected) - {"sp100", "nasdaq100", "taiwan50"})
    if invalid:
        raise ValueError(f"Unknown universes: {invalid}")

    constituents = load_universes(selected, args.allow_taiwan50_fallback)
    constituents.to_csv(out_dir / "market_universe_constituents.csv", index=False, encoding="utf-8-sig")

    all_quality = []
    all_errors = []
    for universe, group in constituents.groupby("universe", sort=False):
        tickers = group["ticker"].tolist()
        print(f"Downloading {universe}: {len(tickers)} tickers")
        wide, errors = download_prices_for_universe(
            universe,
            tickers,
            args.start,
            args.end,
            args.batch_size,
            args.pause_sec,
        )
        wide.to_csv(out_dir / f"{universe.lower()}_adj_close_wide.csv", encoding="utf-8-sig")
        write_long_prices(universe, wide, out_dir / f"{universe.lower()}_prices_long.csv")
        quality = quality_report(universe, wide, args.start, args.end)
        all_quality.append(quality)
        all_errors.extend(errors)

        low_coverage = quality[quality["coverage"] < args.min_coverage] if not quality.empty else quality
        print(
            f"{universe}: downloaded {wide.shape[1]} columns, {wide.shape[0]} dates, "
            f"low coverage={len(low_coverage)}"
        )

    quality_all = pd.concat(all_quality, ignore_index=True) if all_quality else pd.DataFrame()
    quality_all.to_csv(out_dir / "price_download_quality.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_errors, columns=["universe", "ticker", "error"]).to_csv(
        out_dir / "price_download_errors.csv", index=False, encoding="utf-8-sig"
    )

    manifest_rows = []
    for path in sorted(out_dir.glob("*_prices_long.csv")):
        universe = path.name.replace("_prices_long.csv", "").upper()
        q = quality_all[quality_all["universe"] == universe]
        manifest_rows.append(
            {
                "universe": universe,
                "long_prices": str(path),
                "wide_prices": str(out_dir / f"{universe.lower()}_adj_close_wide.csv"),
                "tickers": int(q["ticker"].nunique()) if not q.empty else 0,
                "mean_coverage": float(q["coverage"].mean()) if not q.empty else 0.0,
                "min_coverage": float(q["coverage"].min()) if not q.empty else 0.0,
            }
        )
    pd.DataFrame(manifest_rows).to_csv(out_dir / "market_price_manifest.csv", index=False, encoding="utf-8-sig")
    print(f"Done. Output: {out_dir}")


if __name__ == "__main__":
    main()
