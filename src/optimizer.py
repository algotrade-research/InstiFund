import optuna
from src.backtest import Backtesting
from src.evaluate import Evaluate
from src.settings import logger, config
import pandas as pd
from typing import Dict, Any
from datetime import datetime


class Optimizer:
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date

    def objective_function(self, trial: optuna.Trial) -> float:
        """
        Objective function to maximize using Optuna.
        :param trial: Optuna trial object.
        :return: Objective value to maximize.
        """
        # Define the parameter search space
        params = config["default_backtest_params"]
        params["trailing_stop_loss"] = trial.suggest_float(
            "trailing_stop_loss", 0.05, 0.5, step=0.025)
        params["number_of_stocks"] = trial.suggest_int(
            "number_of_stocks", 1, 5, step=1)
        params["stock_weight_option"] = trial.suggest_categorical(
            "stock_weight_option", ["softmax", "equal", "linear"])
        params["take_profit"] = trial.suggest_float(
            "take_profit", 0.05, 0.5, step=0.025)
        params["institutional_weight"] = trial.suggest_float(
            "institutional_weight", 0.025, 0.975, step=0.025)
        params["roe"] = trial.suggest_float(
            "roe", 0.05, 0.5, step=0.025)
        max_range = 1 - params["roe"] - 0.1
        params["revenue_growth"] = trial.suggest_float(
            "revenue_growth", min(max_range, 0.05),
            min(max_range, 0.5)//0.025 * 0.025, step=0.025)
        max_range = 1 - params["roe"] - params["revenue_growth"] - 0.05
        params["pe"] = trial.suggest_float(
            "pe", min(max_range, 0.05),
            min(max_range, 0.5) // 0.025 * 0.025, step=0.025)

        # Run the backtest with the sampled parameters
        backtest = Backtesting(
            start_date=self.start_date,
            end_date=self.end_date,
            params=params
        )
        backtest.run()
        data = pd.DataFrame(backtest.portfolio_statistics)
        results = Evaluate(data,
                           name=f"backtest_trial_{trial.number}"
                           ).quick_evaluate()
        results["roi"] /= 100
        target = 0.3 * results["roi"] + 0.4 * results["sharpe"] \
            + 0.3 * results["mdd"]
        return target

    def optimize(self, n_trials: int = 100) -> Dict[str, Any]:
        """
        Run the optimization process using Optuna.
        :param n_trials: Number of trials to run.
        :return: Best parameters found during optimization.
        """
        logger.info("Starting optimization with Optuna...")
        study = optuna.create_study(direction="maximize")
        study.optimize(self.objective_function,
                       n_trials=n_trials, show_progress_bar=True)
        logger.info(
            f"Optimization completed. Best parameters: {study.best_params}")
        logger.info(f"Best value: {study.best_value:.2f}%")
        return study.best_params


if __name__ == "__main__":
    # Define the backtesting date range
    start_date = datetime(2023, 2, 1)
    end_date = datetime(2024, 1, 31)

    # Initialize the optimizer
    optimizer = Optimizer(start_date=start_date, end_date=end_date)

    # Run the optimization
    best_params = optimizer.optimize(n_trials=50)
    logger.info(f"Best parameters: {best_params}")

    # backtest with the best parameters
    params = config["default_backtest_params"]
    params.update(best_params)
    backtest = Backtesting(
        start_date=start_date,
        end_date=end_date,
        params=params
    )
    backtest.run()
    data = pd.DataFrame(backtest.portfolio_statistics)
    results = Evaluate(data, name="final_backtest").quick_evaluate()
    logger.info(f"Final backtest results: {results}")
