import optuna.visualization.matplotlib as optuna_matplotlib
import os
import matplotlib.pyplot as plt
import optuna
from src.backtest import Backtesting
from src.evaluate import Evaluate
from src.settings import logger, config, DATA_PATH
import pandas as pd
from typing import Dict, Any
from datetime import datetime
import argparse


class Optimizer:
    def __init__(self, start_date: datetime, end_date: datetime):
        self.start_date = start_date
        self.end_date = end_date
        self.study = None  # Store the study object for reuse

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
        max_range = round(1.0 - params["roe"], 3)
        params["revenue_growth"] = trial.suggest_float(
            "revenue_growth", min(max_range, 0.05),
            min(max_range, 0.5), step=0.025)
        max_range = round(1.0 - params["roe"] - params["revenue_growth"], 3)
        params["pe"] = trial.suggest_float(
            "pe", min(max_range, 0.05),
            min(max_range, 0.5), step=0.025)

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
        mdd_score = (1.0 if results["mdd"] >= -0.15
                     else 1 - ((-0.15) - results["mdd"])/((-0.15) - (-1.0)))
        sharpe_score = (1.0 if results["sharpe"] >= 3.0
                        else results["sharpe"]/3.0)
        target = 0.6 * sharpe_score + 0.4 * mdd_score
        return target

    def optimize(self, n_trials: int = 100) -> None:
        """
        Run the optimization process using Optuna.
        :param n_trials: Number of trials to run.
        """
        logger.info("Starting optimization with Optuna...")

        # Set the random seed for reproducibility
        random_seed = config.get("random_seed", 42)
        sampler = optuna.samplers.TPESampler(seed=random_seed)

        # Create the study with the sampler
        logger.disabled = True
        self.study = optuna.create_study(direction="maximize", sampler=sampler)
        self.study.optimize(self.objective_function,
                            n_trials=n_trials, show_progress_bar=True)
        logger.disabled = config.get("disable_logging", False)

        logger.info(
            f"Optimization completed. Best parameters: {self.study.best_params}")
        logger.info(f"Best value: {self.study.best_value:.2f}%")

    def save_trials_data(self, output_dir: str) -> None:
        """
        Save the trials data to a CSV file.
        :param output_dir: Directory to save the trials data.
        """
        if not self.study:
            raise ValueError("No study found. Run optimize() first.")
        trials_df = self.study.trials_dataframe(
            attrs=("number", "value", "params", "state"))
        trials_file = os.path.join(output_dir, "trials.csv")
        trials_df.to_csv(trials_file, index=False)
        logger.info(f"Trials data saved to {trials_file}")

    def plot_optimization_results(self, output_dir: str) -> None:
        """
        Generate and save plots for the optimization results.
        :param output_dir: Directory to save the plots.
        """
        if not self.study:
            raise ValueError("No study found. Run optimize() first.")

        # Plot optimization history using Matplotlib
        fig1 = optuna_matplotlib.plot_optimization_history(self.study)
        fig1.figure.savefig(os.path.join(
            output_dir, "optimization_history.png"))

        # Plot parameter importance using Matplotlib
        fig2 = optuna_matplotlib.plot_param_importances(self.study)
        fig2.figure.savefig(os.path.join(output_dir, "param_importance.png"))

        logger.info(f"Optimization plots saved to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Optimize backtest parameters using Optuna.")
    parser.add_argument("--n_trials", type=int, default=100,
                        help="Number of trials to run.")
    args = parser.parse_args()
    # Define the backtesting date range
    start_date = datetime.strptime(
        config["in_sample"]["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(config["in_sample"]["end_date"], "%Y-%m-%d")

    # Initialize the optimizer
    optimizer = Optimizer(start_date=start_date, end_date=end_date)

    # Run the optimization
    optimizer.optimize(n_trials=args.n_trials)

    # Define the output directory
    output_dir = os.path.join(DATA_PATH, "optimization")
    os.makedirs(output_dir, exist_ok=True)

    # Save trials data and plots
    optimizer.save_trials_data(output_dir)
    optimizer.plot_optimization_results(output_dir)

    # Backtest with the best parameters
    best_params = optimizer.study.best_params
    params = config["default_backtest_params"]
    params.update(best_params)
    backtest = Backtesting(
        start_date=start_date,
        end_date=end_date,
        params=params
    )
    backtest.run()

    # Save the backtest results
    optimized_result_dir = os.path.join(
        DATA_PATH, "backtest", "optimized_in_sample")
    os.makedirs(optimized_result_dir, exist_ok=True)
    backtest.evaluate(result_dir=optimized_result_dir)
    backtest.save_portfolio(result_dir=optimized_result_dir)
