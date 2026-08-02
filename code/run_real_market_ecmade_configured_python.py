from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

from ecmade_moo import ECMADEMOO, ECMADEMOOConfig, Problem, cardinality_simplex_repair


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
ASSIGNMENT = BASE_DIR / "config_protocol_assignments" / "real_market_ecmade_configuration_assignment.csv"
WINDOW_MANIFEST = BASE_DIR / "windows" / "rolling_window_manifest.csv"
DEFAULT_OUT = BASE_DIR / "raw_configured_ecmade"
METHODS = [
    "HandCrafted_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
    "MetaDesigned_ECMADE_MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO",
]


def text_value(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value)


def numeric_value(row: pd.Series, column: str, default: float) -> float:
    if column not in row.index or pd.isna(row[column]):
        return default
    return float(row[column])


def int_value(row: pd.Series, column: str, default: int) -> int:
    return int(round(numeric_value(row, column, default)))


def build_problem(data_path: Path, k_value: int) -> tuple[Problem, dict]:
    data = loadmat(data_path)
    mu = np.asarray(data["mu"], dtype=float).reshape(-1)
    sigma = np.asarray(data["Sigma"], dtype=float)
    sigma = 0.5 * (sigma + sigma.T)
    d = len(mu)
    lower = np.zeros(d)
    upper = np.ones(d)

    def repair(x: np.ndarray) -> np.ndarray:
        return cardinality_simplex_repair(x, lower, upper, k_value)

    def evaluate(x: np.ndarray) -> np.ndarray:
        w = repair(x)
        risk = float(w @ sigma @ w)
        ret = float(w @ mu)
        return np.array([risk, -ret], dtype=float)

    problem = Problem(
        name=data_path.stem,
        num_obj=2,
        num_var=d,
        lower=lower,
        upper=upper,
        evaluate=evaluate,
        repair=repair,
    )
    tickers = [str(x[0]) if isinstance(x, np.ndarray) else str(x) for x in data["tickers"].reshape(-1)]
    return problem, {
        "mu": mu,
        "Sigma": sigma,
        "testReturns": np.asarray(data["testReturns"], dtype=float),
        "tickers": tickers,
    }


def config_from_assignment(row: pd.Series, run: int, pop_size: int, max_fe: int) -> ECMADEMOOConfig:
    return ECMADEMOOConfig(
        pop_size=pop_size,
        max_fe=max_fe,
        subpops=int_value(row, "subpops", 3),
        theta=numeric_value(row, "theta", 1 / 13),
        stagnation_threshold=int_value(row, "stagnationThreshold", 50),
        seed=run,
        exchange_mode=text_value(row.get("exchangeMode", "paper"), "paper"),
        elite_ratio=numeric_value(row, "eliteRatio", 0.05),
        operator_mode=text_value(row.get("operatorMode", "mixed"), "mixed"),
        consensus_archive=bool(int_value(row, "consensusArchive", 0)),
        archive_consensus_weight=numeric_value(row, "archiveConsWeight", 0.0),
        best_guide=text_value(row.get("bestGuide", "rank"), "rank"),
        min_subpop_size=int_value(row, "minSubpopSize", 1),
        archive_limit_factor=int_value(row, "archiveLimitFactor", 5),
    )


def save_matrix(path: Path, matrix: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, np.asarray(matrix, dtype=float), delimiter=",")


def feasible_rate(dec: np.ndarray, k_value: int) -> float:
    if dec.size == 0:
        return math.nan
    card = (dec > 1e-8).sum(axis=1)
    sum_ok = np.abs(dec.sum(axis=1) - 1.0) <= 1e-6
    bounds_ok = np.all(dec >= -1e-8, axis=1) & np.all(dec <= 1.0 + 1e-8, axis=1)
    return float(np.mean((card <= k_value) & sum_ok & bounds_ok))


def constraint_violation(dec: np.ndarray, k_value: int) -> np.ndarray:
    if dec.size == 0:
        return np.array([math.nan])
    card = np.maximum((dec > 1e-8).sum(axis=1) - k_value, 0)
    sum_violation = np.abs(dec.sum(axis=1) - 1.0)
    lower = np.maximum(-dec, 0).sum(axis=1)
    upper = np.maximum(dec - 1.0, 0).sum(axis=1)
    return card + sum_violation + lower + upper


def archive_diversity(obj: np.ndarray) -> float:
    if len(obj) <= 1:
        return 0.0
    return float(np.linalg.norm(obj.max(axis=0) - obj.min(axis=0)))


def archive_spacing(obj: np.ndarray) -> float:
    if len(obj) <= 2:
        return 0.0
    diff = obj[:, None, :] - obj[None, :, :]
    dist = np.sqrt((diff * diff).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    nearest = np.min(dist, axis=1)
    nearest = nearest[np.isfinite(nearest)]
    return float(np.std(nearest)) if len(nearest) else 0.0


def save_run_outputs(run_dir: Path, result, runtime: float, row: pd.Series, data: dict, transaction_cost: float) -> None:
    k_value = int(row["K"])
    run_dir.mkdir(parents=True, exist_ok=True)
    dec = result.variables
    obj = result.objectives
    pf_dec = result.pareto_variables
    pf_obj = result.pareto_objectives
    save_matrix(run_dir / "population_dec.csv", dec)
    save_matrix(run_dir / "population_obj.csv", obj)
    save_matrix(run_dir / "pf_dec.csv", pf_dec)
    save_matrix(run_dir / "pf_obj.csv", pf_obj)
    save_matrix(run_dir / "final_archive_dec.csv", pf_dec)
    save_matrix(run_dir / "final_archive_obj.csv", pf_obj)
    save_matrix(run_dir / "pf_points.csv", pf_obj)
    pd.DataFrame({"runtime_sec": [runtime]}).to_csv(run_dir / "runtime.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "PF_Feasible_Rate": [feasible_rate(pf_dec, k_value)],
            "Population_Feasible_Rate": [feasible_rate(dec, k_value)],
        }
    ).to_csv(run_dir / "feasible_rate.csv", index=False, encoding="utf-8-sig")
    pf_v = constraint_violation(pf_dec, k_value)
    pop_v = constraint_violation(dec, k_value)
    pd.DataFrame(
        {
            "PF_Mean_Violation": [float(np.nanmean(pf_v))],
            "PF_Max_Violation": [float(np.nanmax(pf_v))],
            "Population_Mean_Violation": [float(np.nanmean(pop_v))],
            "Population_Max_Violation": [float(np.nanmax(pop_v))],
            "PF_Feasible_Rate": [feasible_rate(pf_dec, k_value)],
            "Population_Feasible_Rate": [feasible_rate(dec, k_value)],
        }
    ).to_csv(run_dir / "constraint_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "Archive_Size": [len(pf_obj)],
            "Archive_Diversity": [archive_diversity(pf_obj)],
            "Archive_Spacing": [archive_spacing(pf_obj)],
        }
    ).to_csv(run_dir / "archive_metrics.csv", index=False, encoding="utf-8-sig")
    save_selected_backtest(run_dir, pf_dec, pf_obj, data, transaction_cost)


def save_metadata(run_dir: Path, row: pd.Series, cfg: ECMADEMOOConfig, runs: int, transaction_cost: float) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "method": row["method"],
        "universe": row["universe"],
        "window_id": row["window_id"],
        "data_path": row["data_path"],
        "train_start": row.get("train_start", ""),
        "train_end": row.get("train_end", ""),
        "test_start": row.get("test_start", ""),
        "test_end": row.get("test_end", ""),
        "assets": int(row["assets"]),
        "K": int(row["K"]),
        "train_days": int(row.get("train_days", 0)),
        "test_days": int(row.get("test_days", 0)),
        "N": cfg.pop_size,
        "maxFE": cfg.max_fe,
        "runs": runs,
        "transaction_cost": transaction_cost,
        "theta_id": row["theta_id"],
        "source_theta_id": row.get("source_theta_id", ""),
        "subpops": cfg.subpops,
        "operatorMode": cfg.operator_mode,
        "exchangeMode": cfg.exchange_mode,
        "eliteRatio": cfg.elite_ratio,
        "stagnationThreshold": cfg.stagnation_threshold,
        "theta": cfg.theta,
        "archiveLimitFactor": cfg.archive_limit_factor,
        "consensusArchive": cfg.consensus_archive,
        "archiveConsWeight": cfg.archive_consensus_weight,
        "bestGuide": cfg.best_guide,
        "minSubpopSize": cfg.min_subpop_size,
    }
    pd.DataFrame([data]).to_csv(run_dir / "window_metadata.csv", index=False, encoding="utf-8-sig")


def save_selected_backtest(run_dir: Path, pf_dec: np.ndarray, pf_obj: np.ndarray, data: dict, transaction_cost: float) -> None:
    if len(pf_dec) == 0:
        return
    train_return = -pf_obj[:, 1]
    train_risk = np.sqrt(np.maximum(pf_obj[:, 0], 0))
    sharpe = train_return / np.maximum(train_risk, 1e-12)
    idx = int(np.nanargmax(sharpe))
    w = pf_dec[idx].astype(float)
    w = w / max(float(w.sum()), 1e-12)
    selected = w > 1e-8
    pd.DataFrame(
        {
            "ticker": data["tickers"],
            "weight": w,
            "selected": selected,
        }
    ).to_csv(run_dir / "selected_portfolio.csv", index=False, encoding="utf-8-sig")

    r = np.asarray(data["testReturns"], dtype=float) @ w
    r = np.asarray(r, dtype=float).reshape(-1)
    gross = float(np.prod(1.0 + r) - 1.0)
    days = max(len(r), 1)
    ann_return = float((1.0 + gross) ** (252.0 / days) - 1.0)
    ann_vol = float(np.std(r) * np.sqrt(252))
    sharpe_oos = float(np.mean(r) / max(np.std(r), 1e-12) * np.sqrt(252))
    downside = r[r < 0]
    sortino = float(np.mean(r) / max(np.std(downside), 1e-12) * np.sqrt(252)) if len(downside) else math.inf
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(equity)
    mdd = float(np.min(equity / peak - 1.0))
    turnover = float(np.sum(np.abs(w)))
    tc_cost = float(transaction_cost * turnover)
    net_return = gross - tc_cost
    ann_net = float((1.0 + net_return) ** (252.0 / days) - 1.0)
    pd.DataFrame(
        {
            "gross_return": [gross],
            "net_return": [net_return],
            "annual_return": [ann_return],
            "annual_net_return": [ann_net],
            "annual_volatility": [ann_vol],
            "sharpe": [sharpe_oos],
            "sortino": [sortino],
            "max_drawdown": [mdd],
            "turnover": [turnover],
            "transaction_cost": [tc_cost],
        }
    ).to_csv(run_dir / "backtest_metrics.csv", index=False, encoding="utf-8-sig")
    save_matrix(run_dir / "test_daily_returns.csv", r.reshape(-1, 1))


def complete_run(run_dir: Path) -> bool:
    required = ["pf_obj.csv", "pf_dec.csv", "selected_portfolio.csv", "backtest_metrics.csv", "runtime.csv"]
    return all((run_dir / name).exists() for name in required)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignment", type=Path, default=ASSIGNMENT)
    parser.add_argument("--window-manifest", type=Path, default=WINDOW_MANIFEST)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--pop-size", type=int, default=100)
    parser.add_argument("--max-fe", type=int, default=10000)
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--transaction-cost", type=float, default=0.001)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assignment = pd.read_csv(args.assignment, encoding="utf-8-sig")
    manifest = pd.read_csv(args.window_manifest, encoding="utf-8-sig")
    manifest_cols = [
        "universe",
        "window_id",
        "data_path",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "train_days",
        "test_days",
        "min_train_coverage",
        "min_test_coverage",
    ]
    assignment = assignment.merge(manifest[manifest_cols], on=["universe", "window_id"], how="left")
    if assignment["data_path"].isna().any():
        missing = assignment.loc[assignment["data_path"].isna(), ["universe", "window_id"]].drop_duplicates()
        raise RuntimeError(f"Missing window manifest rows:\n{missing.to_string(index=False)}")
    methods = [part.strip() for part in args.methods.split(",") if part.strip()]
    assignment = assignment[assignment["method"].isin(methods)].copy()
    if args.max_windows is not None:
        keep_windows = assignment[["universe", "window_id"]].drop_duplicates().head(args.max_windows)
        assignment = assignment.merge(keep_windows, on=["universe", "window_id"], how="inner")
    total = len(assignment) * args.runs
    done = 0
    for _, row in assignment.iterrows():
        data_path = Path(row["data_path"])
        problem, data = build_problem(data_path, int(row["K"]))
        for run in range(1, args.runs + 1):
            run_dir = args.out_root / str(row["universe"]) / str(row["window_id"]) / str(row["method"]) / f"run_{run:03d}"
            if not args.force and complete_run(run_dir):
                done += 1
                continue
            cfg = config_from_assignment(row, run, args.pop_size, args.max_fe)
            save_metadata(run_dir, row, cfg, args.runs, args.transaction_cost)
            start = time.perf_counter()
            result = ECMADEMOO(problem, cfg).run()
            runtime = time.perf_counter() - start
            save_run_outputs(run_dir, result, runtime, row, data, args.transaction_cost)
            done += 1
            print(
                f"[{done}/{total}] {row['method']} {row['universe']} {row['window_id']} "
                f"run={run:03d} theta={row['theta_id']} runtime={runtime:.2f}s",
                flush=True,
            )


if __name__ == "__main__":
    main()
