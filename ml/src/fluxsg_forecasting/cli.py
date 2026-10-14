import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fluxsg_forecasting.drift import assess_drift
from fluxsg_forecasting.features import build_features, load_history
from fluxsg_forecasting.fetch import fetch_history
from fluxsg_forecasting.model import run_experiment


def csv_inputs(input_dir: Path) -> list[Path]:
    paths = sorted(input_dir.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSV history found in {input_dir}")
    return paths


def command_fetch(args: argparse.Namespace) -> dict[str, Any]:
    return fetch_history(args.output_dir)


def command_train(args: argparse.Namespace) -> dict[str, Any]:
    return run_experiment(
        csv_inputs(args.input_dir),
        args.output_dir,
        max_iter=args.max_iter,
        backtest_folds=args.backtest_folds,
    )


def command_monitor(args: argparse.Namespace) -> dict[str, Any]:
    reference = json.loads(args.reference.read_text())
    history = load_history(csv_inputs(args.input_dir))
    features = build_features(history)
    if args.recent_hours:
        cutoff = features["timestamp"].max() - pd.Timedelta(hours=args.recent_hours)
        features = features.loc[features["timestamp"] >= cutoff]
    report = assess_drift(features, reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="FluxSG regional PSI forecasting")
    commands = root.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", help="Download official NEA PSI history")
    fetch.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    fetch.set_defaults(handler=command_fetch)

    train = commands.add_parser("train", help="Run the chronological forecasting experiment")
    train.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    train.add_argument("--output-dir", type=Path, default=Path("artifacts/latest"))
    train.add_argument("--max-iter", type=int, default=250)
    train.add_argument("--backtest-folds", type=int, default=4)
    train.set_defaults(handler=command_train)

    monitor = commands.add_parser("monitor", help="Compare recent features with training data")
    monitor.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    monitor.add_argument(
        "--reference", type=Path, default=Path("artifacts/latest/training_reference.json")
    )
    monitor.add_argument("--output", type=Path, default=Path("artifacts/latest/drift_live.json"))
    monitor.add_argument("--recent-hours", type=int, default=24 * 30)
    monitor.set_defaults(handler=command_monitor)
    return root


def main() -> None:
    arguments = parser().parse_args()
    result = arguments.handler(arguments)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
