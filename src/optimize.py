import optuna.visualization.matplotlib as optuna_matplotlib
from optuna.study import MaxTrialsCallback
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
    def __init__(self, start_date: datetime, end_date: datetime,
                 result_dir: str, n_stocks: int) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.n_stocks = n_stocks
        self.result_dir = result_dir
        self.study = None  # Store the study object for reuse

        # Set the random seed for reproducibility
        random_seed = config.get("random_seed", 42)
        sampler = optuna.samplers.TPESampler(seed=random_seed)
        # Create the study object
        storage_path = f"sqlite:///{
            os.path.join(result_dir, config['optuna']['storage_name'])}.db"
        os.makedirs(result_dir, exist_ok=True)
        logger.info(
            f"Creating Optuna study with storage path: {storage_path}"
        )
        self.study = optuna.create_study(
            study_name=config["optuna"]["study_name"],
            storage=storage_path,
            sampler=sampler,
            load_if_exists=True,
            direction="maximize",
        )

    def objective_function(self, trial: optuna.Trial) -> float:
        """
        Objective function to maximize using Optuna.
        :param trial: Optuna trial object.
        :return: Objective value to maximize.
        """
        # Define the parameter search space
        params = config["default_backtest_params"]
        params["n_stocks"] = self.n_stocks
        params["trailing_stop_loss"] = trial.suggest_float(
            "trailing_stop_loss", 0.05, 0.5, step=0.025)
        params["stock_weight_option"] = trial.suggest_categorical(
            "stock_weight_option", ["softmax", "equal", "linear"])
        params["take_profit"] = trial.suggest_float(
            "take_profit", 0.05, 0.5, step=0.025)

        params["institutional_weight"] = trial.suggest_float(
            "institutional_weight", 0.025, 0.975, step=0.025)
        params["fund_net_buying"] = trial.suggest_float(
            "fund_net_buying", 0.05, 0.9, step=0.025)
        max_range = round(
            1.0 - params["fund_net_buying"] - 0.025, 3)
        params["number_fund_holdings"] = trial.suggest_float(
            "number_fund_holdings", min(max_range, 0.05),
            min(max_range, 0.9), step=0.025)

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
        mdd_score = (1.0 if results["mdd"] >= -0.05
                     else 0.0 if results["mdd"] <= -0.20
                     else (0.2 + results["mdd"])/0.15)
        sharpe_score = (1.0 if results["sharpe"] >= 3.0
                        else results["sharpe"]/3.0)
        target = 0.8 * sharpe_score + 0.2 * mdd_score
        return target

    def optimize(self, n_trials: int = 100) -> None:
        """
        Run the optimization process using Optuna.
        :param n_trials: Number of trials to run.
        """
        logger.info("Starting optimization with Optuna...")
        logger.disabled = True
        self.study.optimize(self.objective_function,
                            n_trials=n_trials,
                            show_progress_bar=True)
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

        # Reset Matplotlib style to default
        plt.style.use("default")
        logger.info(f"Optimization plots saved to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Optimize backtest parameters using Optuna.")
    parser.add_argument("--n_trials", type=int, default=100,
                        help="Number of trials to run.")
    parser.add_argument("--n_stocks", type=int, default=3,
                        help="Number of stocks to select each month.")
    args = parser.parse_args()
    # Define the backtesting date range
    start_date = datetime.strptime(
        config["in_sample"]["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(config["in_sample"]["end_date"], "%Y-%m-%d")

    # Define the output directory
    output_dir = os.path.join(DATA_PATH, "optimization")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the optimizer
    optimizer = Optimizer(start_date=start_date,
                          end_date=end_date,
                          result_dir=output_dir,
                          n_stocks=args.n_stocks)

    # Run the optimization
    remaining_trials = args.n_trials - len(optimizer.study.trials)
    logger.info(
        f"Remaining trials to run: {remaining_trials} out of "
        f"{args.n_trials} total trials.")

    if remaining_trials > 0:
        optimizer.optimize(n_trials=remaining_trials)
    else:
        logger.info("No remaining trials to run.")

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
