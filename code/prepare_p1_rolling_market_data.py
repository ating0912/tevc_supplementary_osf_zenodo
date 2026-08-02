from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import savemat


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "data"
DEFAULT_OUT = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "windows"


def read_wide_prices(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df.columns = [str(c).upper() for c in df.columns]
    return df.apply(pd.to_numeric, errors="coerce")


def window_bounds(index: pd.DatetimeIndex, train_years: int, test_months: int) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    first = index.min().normalize()
    last = index.max().normalize()
    train_start = first
    bounds = []
    while True:
        train_end = train_start + pd.DateOffset(years=train_years) - pd.DateOffset(days=1)
        test_start = train_end + pd.DateOffset(days=1)
        test_end = test_start + pd.DateOffset(months=test_months) - pd.DateOffset(days=1)
        if test_end > last:
            break
        bounds.append((train_start, train_end, test_start, test_end))
        train_start = train_start + pd.DateOffset(months=test_months)
    return bounds


def select_assets(
    prices: pd.DataFrame,
    train: pd.DataFrame,
    test: pd.DataFrame,
    min_coverage: float,
    max_assets: int,
) -> list[str]:
    train_cov = train.notna().mean()
    test_cov = test.notna().mean()
    ok = train_cov.ge(min_coverage) & test_cov.ge(min_coverage)
    candidates = train.columns[ok].tolist()
    if len(candidates) <= max_assets:
        return candidates
    returns = prices[candidates].ffill().pct_change(fill_method=None)
    score = returns.loc[train.index].std().replace([np.inf, -np.inf], np.nan).fillna(0)
    return score.sort_values(ascending=False).head(max_assets).index.tolist()


def clean_returns(prices: pd.DataFrame) -> pd.DataFrame:
    filled = prices.ffill().dropna(axis=1, how="any")
    returns = filled.pct_change(fill_method=None).iloc[1:]
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    return returns


def save_window(
    out_path: Path,
    tickers: list[str],
    train_returns: pd.DataFrame,
    test_returns: pd.DataFrame,
    train_bounds: tuple[pd.Timestamp, pd.Timestamp],
    test_bounds: tuple[pd.Timestamp, pd.Timestamp],
    k: int,
    universe: str,
    window_id: str,
) -> None:
    mu = train_returns.mean().to_numpy(dtype=float)
    sigma = np.cov(train_returns.to_numpy(dtype=float), rowvar=False)
    sigma = np.atleast_2d(0.5 * (sigma + sigma.T))
    savemat(
        out_path,
        {
            "mu": mu.reshape(-1, 1),
            "Sigma": sigma,
            "trainReturns": train_returns.to_numpy(dtype=float),
            "testReturns": test_returns.to_numpy(dtype=float),
            "tickers": np.array(tickers, dtype=object),
            "trainStart": train_bounds[0].date().isoformat(),
            "trainEnd": train_bounds[1].date().isoformat(),
            "testStart": test_bounds[0].date().isoformat(),
            "testEnd": test_bounds[1].date().isoformat(),
            "K": int(k),
            "universe": universe,
            "windowId": window_id,
        },
    )


def prepare_universe(
    universe: str,
    prices: pd.DataFrame,
    out_dir: Path,
    train_years: int,
    test_months: int,
    k: int,
    min_coverage: float,
    min_assets: int,
    max_assets: int,
    max_windows: int | None,
) -> list[dict]:
    rows = []
    bounds = window_bounds(prices.index, train_years, test_months)
    if max_windows is not None:
        bounds = bounds[:max_windows]
    universe_dir = out_dir / universe
    universe_dir.mkdir(parents=True, exist_ok=True)
    for idx, (train_start, train_end, test_start, test_end) in enumerate(bounds, start=1):
        train_prices = prices.loc[(prices.index >= train_start) & (prices.index <= train_end)]
        test_prices = prices.loc[(prices.index >= test_start) & (prices.index <= test_end)]
        selected = select_assets(prices, train_prices, test_prices, min_coverage, max_assets)
        if len(selected) < min_assets:
            continue
        train_returns = clean_returns(train_prices[selected])
        test_returns = clean_returns(test_prices[selected])
        common = [c for c in selected if c in train_returns.columns and c in test_returns.columns]
        train_returns = train_returns[common]
        test_returns = test_returns[common]
        if len(common) < min_assets or len(test_returns) < 20:
            continue
        window_id = f"window_{idx:03d}"
        data_path = universe_dir / f"{window_id}.mat"
        save_window(
            data_path,
            common,
            train_returns,
            test_returns,
            (train_start, train_end),
            (test_start, test_end),
            min(k, len(common)),
            universe,
            window_id,
        )
        rows.append(
            {
                "universe": universe,
                "window_id": window_id,
                "data_path": str(data_path),
                "train_start": train_start.date().isoformat(),
                "train_end": train_end.date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": test_end.date().isoformat(),
                "assets": len(common),
                "K": min(k, len(common)),
                "train_days": len(train_returns),
                "test_days": len(test_returns),
                "min_train_coverage": float(train_prices[common].notna().mean().min()),
                "min_test_coverage": float(test_prices[common].notna().mean().min()),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--universes", default="NASDAQ100")
    parser.add_argument("--train-years", type=int, default=3)
    parser.add_argument("--test-months", type=int, default=6)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--min-coverage", type=float, default=0.95)
    parser.add_argument("--min-assets", type=int, default=30)
    parser.add_argument("--max-assets", type=int, default=60)
    parser.add_argument("--max-windows", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir if args.data_dir.is_absolute() else ROOT / args.data_dir
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = [part.strip().upper() for part in args.universes.split(",") if part.strip()]
    rows = []
    for universe in selected:
        wide_path = data_dir / f"{universe.lower()}_adj_close_wide.csv"
        if not wide_path.exists():
            raise FileNotFoundError(wide_path)
        prices = read_wide_prices(wide_path)
        rows.extend(
            prepare_universe(
                universe,
                prices,
                out_dir,
                args.train_years,
                args.test_months,
                args.k,
                args.min_coverage,
                args.min_assets,
                args.max_assets,
                args.max_windows,
            )
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(out_dir / "rolling_window_manifest.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote {len(manifest)} rolling windows to {out_dir}")
    if not manifest.empty:
        print(manifest[["universe", "window_id", "train_start", "train_end", "test_start", "test_end", "assets", "K", "test_days"]].to_string(index=False))


if __name__ == "__main__":
    main()
