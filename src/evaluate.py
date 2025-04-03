from src.settings import config, logger, DATA_PATH
from matplotlib import pyplot as plt
from datetime import datetime
import pandas as pd
import json
from typing import Dict, Any
import os
import argparse
from src.vnindex import get_vnindex_benchmark


class Evaluate:
    """
    Evaluate the performance of a trading strategy, comparing it
        to a benchmark, by default VNINDEX.

    The input data should be a DataFrame with the following columns:
    - datetime: Date and time of the data point
    - total_assets: Total asset value at that time
    - cash: Cash value at that time
    - number_of_trades: Number of trades executed
    - number_of_winners: Number of winning trades
    - sum_of_winners: Total profit from winning trades
    - sum_of_losers: Total loss from losing trades

    The evaluation includes calculating:
    - Return on investment (ROI)
    - Total P&L
    - Annualized return
    - Sharpe ratio
    - Sortino ratio
    - Calmar ratio
    - Maximum drawdown
    - Compound annual growth rate (CAGR)
    - Win rate
    - Expected return
    - Volatility
    - Max time to recover from drawdown

    Calculate & plot by time:
    - Daily returns
    - Cumulative returns
    - Drawdown
    - Cash flow
    - Benchmark comparison
    """

    def __init__(self, data: pd.DataFrame, name: str = "benchmark") -> None:
        self.data = data
        self.name = name
        self.data["datetime"] = pd.to_datetime(
            self.data["datetime"])
        self.data.set_index("datetime", inplace=True)
        self.data.sort_index(inplace=True)

    def get_roi(self) -> float:
        """
        Calculate the return on investment (ROI).
        ROI = (Final Value - Initial Value) / Initial Value * 100
        """
        initial_value = self.data["total_assets"].iloc[0]
        final_value = self.data["total_assets"].iloc[-1]
        roi = (final_value - initial_value) / initial_value * 100
        return roi

    def get_total_pnl(self) -> float:
        """
        Calculate the total profit and loss (P&L).
        Total P&L = Final Value - Initial Value
        """
        initial_value = self.data["total_assets"].iloc[0]
        final_value = self.data["total_assets"].iloc[-1]
        total_pnl = final_value - initial_value
        return total_pnl

    def get_sharpe_ratio(self,
                         risk_free_rate_annual:
                         float = config["risk_free_rate_annual"]
                         ) -> float:
        """
        Calculate the Sharpe ratio.
        Sharpe Ratio = (Average Return - Risk-Free Rate) / Standard Deviation of Returns
        """
        daily_returns = self.data["total_assets"].pct_change().dropna()
        average_return = daily_returns.mean() * 252
        std_dev = daily_returns.std() * (252 ** 0.5)
        sharpe_ratio = (average_return - risk_free_rate_annual) / std_dev
        return sharpe_ratio

    def get_sortino_ratio(self,
                          risk_free_rate_annual:
                          float = config["risk_free_rate_annual"]
                          ) -> float:
        """
        Calculate the Sortino ratio.
        Sortino Ratio = (Average Return - Risk-Free Rate) / Downside Deviation
        """
        daily_returns = self.data["total_assets"].pct_change().dropna()
        average_return = daily_returns.mean() * 252
        downside_deviation = daily_returns[daily_returns < 0].std(
        ) * (252 ** 0.5)
        sortino_ratio = (average_return -
                         risk_free_rate_annual) / downside_deviation
        return sortino_ratio

    def get_calmar_ratio(self) -> float:
        """
        Calculate the Calmar ratio.
        Calmar Ratio = Annualized Return / Maximum Drawdown
        """
        annualized_return = self.get_cagr() / 100
        max_drawdown = self.get_max_drawdown()
        calmar_ratio = annualized_return / abs(max_drawdown)
        return calmar_ratio

    def get_max_drawdown(self) -> float:
        """
        Calculate the maximum drawdown.
        Maximum Drawdown = (Peak Value - Trough Value) / Peak Value
        """
        rolling_max = self.data["total_assets"].cummax()
        drawdown = (self.data["total_assets"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        return max_drawdown

    def get_cagr(self) -> float:
        """
        Calculate the compound annual growth rate (CAGR).
        CAGR = (Final Value / Initial Value) ^ (1 / Number of Years) - 1
        """
        initial_value = self.data["total_assets"].iloc[0]
        final_value = self.data["total_assets"].iloc[-1]
        num_years = (self.data.index[-1] - self.data.index[0]).days / 365.25
        cagr = (final_value / initial_value) ** (1 / num_years) - 1
        return cagr * 100

    def get_win_rate(self) -> float:
        """
        Calculate the win rate.
        Win Rate = Number of Winning Trades / Total Number of Trades
        """
        win_rate = self.data["number_of_winners"].sum() / \
            self.data["number_of_trades"].sum()
        return win_rate * 100

    def get_expected_return(self) -> float:
        """
        Calculate the expected return.
        Expected Return = (Win Rate * Average Win) - (Loss Rate * Average Loss)
        """
        win_rate = self.get_win_rate() / 100
        loss_rate = 1 - win_rate
        avg_win = self.data["sum_of_winners"].sum() / \
            self.data["number_of_winners"].sum()
        avg_loss = abs(self.data["sum_of_losers"].sum() /
                       self.data["number_of_trades"].sum())
        expected_return = (win_rate * avg_win) - (loss_rate * avg_loss)
        return expected_return * 100

    def get_volatility(self) -> float:
        """
        Calculate the volatility.
        Volatility = Standard Deviation of Daily Returns
        """
        daily_returns = self.data["total_assets"].pct_change().dropna()
        volatility = daily_returns.std() * (252 ** 0.5)
        return volatility * 100

    def get_max_time_to_recover(self) -> float:
        """
        Calculate the maximum time to recover from drawdown.
        Maximum Time to Recover = Maximum Drawdown Duration
        """
        rolling_max = self.data["total_assets"].cummax()
        drawdown = (self.data["total_assets"] - rolling_max) / rolling_max
        drawdown_duration = (drawdown < 0).astype(int).cumsum()
        max_time_to_recover = drawdown_duration.max()
        return max_time_to_recover

    def get_benchmark_comparison(self, benchmark_data: pd.DataFrame | None
                                 ) -> pd.DataFrame:
        """
        Compare the performance of the strategy with a benchmark.
        """
        if benchmark_data is None:
            # If no benchmark data is provided, use VNINDEX as default
            benchmark_data = get_vnindex_benchmark(
                self.data.index[0], self.data.index[-1])

        # Merge the two DataFrames on the datetime index
        comparison_df = pd.merge(self.data, benchmark_data,
                                 left_index=True, right_index=True,
                                 suffixes=('', '_benchmark'))

        # Calculate daily returns for both strategy and benchmark
        comparison_df["cummulative_return"] = (
            comparison_df["total_assets"] / comparison_df["total_assets"].iloc[0]) - 1
        comparison_df["cummulative_return_benchmark"] = (
            comparison_df["total_assets_benchmark"] / comparison_df["total_assets_benchmark"].iloc[0]) - 1
        return comparison_df

    def get_cash_flow(self) -> pd.DataFrame:
        """
        Calculate the cash flow.
        Cash Flow = Total Assets - Cash
        """
        self.data["cash_flow"] = self.data["total_assets"] - self.data["cash"]
        return self.data[["cash_flow"]]

    def get_daily_returns(self) -> pd.DataFrame:
        """
        Calculate daily returns.
        Daily Returns = (Current Value - Previous Value) / Previous Value
        """
        self.data["daily_returns"] = self.data["total_assets"].pct_change()
        return self.data[["daily_returns"]]

    def get_cumulative_returns(self) -> pd.DataFrame:
        """
        Calculate cumulative returns.
        Cumulative Returns = (Current Value / Initial Value) - 1
        """
        self.data["cumulative_returns"] = (
            self.data["total_assets"] / self.data["total_assets"].iloc[0]) - 1
        return self.data[["cumulative_returns"]]

    def plot_daily_returns(self, result_dir: str) -> None:
        """
        Plot and save daily returns.
        """
        plt.figure()
        self.get_daily_returns()
        self.data["daily_returns"].plot(title="Daily Returns",
                                        color="#1f77b4")
        plt.xlabel("Date")
        plt.ylabel("Daily Returns")
        plt.tight_layout()
        plt.savefig(f"{result_dir}/daily_returns.png")
        plt.close()

    def plot_cumulative_returns(self, result_dir: str) -> None:
        """
        Plot and save cumulative returns.
        """
        plt.figure()
        self.get_cumulative_returns()
        self.data["cumulative_returns"].plot(title="Cumulative Returns",
                                             color="#1f77b4")
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")
        plt.tight_layout()
        plt.savefig(f"{result_dir}/cumulative_returns.png")
        plt.close()

    def plot_drawdown(self, result_dir: str) -> None:
        """
        Plot and save drawdown.
        """
        rolling_max = self.data["total_assets"].cummax()
        drawdown = (self.data["total_assets"] - rolling_max) / rolling_max
        plt.figure()
        drawdown.plot(title="Drawdown",
                      color="#1f77b4")
        plt.xlabel("Date")
        plt.ylabel("Drawdown")
        plt.tight_layout()
        plt.savefig(f"{result_dir}/drawdown.png")
        plt.close()

    def plot_benchmark_comparison(self, benchmark_data: pd.DataFrame | None,
                                  result_dir: str) -> None:
        """
        Plot and save benchmark comparison with less attractive color for the benchmark.
        """
        comparison_df = self.get_benchmark_comparison(benchmark_data)
        plt.figure()
        comparison_df[["cummulative_return", "cummulative_return_benchmark"]].plot(
            title="Benchmark Comparison",
            color=["#1f77b4", "#ff7f0e"]
        )
        plt.xlabel("Date")
        plt.ylabel("Cumulative Returns")
        plt.legend(["Strategy", "Benchmark (default: VNINDEX)"])
        plt.grid()
        plt.tight_layout()
        plt.savefig(f"{result_dir}/benchmark_comparison.png")
        plt.close()

    def plot_all(self, benchmark_data: pd.DataFrame | None,
                 result_dir: str) -> None:
        """
        Plot and save all evaluation metrics.
        """
        self.plot_daily_returns(result_dir)
        self.plot_cumulative_returns(result_dir)
        self.plot_drawdown(result_dir)
        if self.name != "vnindex":
            self.plot_cash_flow(result_dir)
            self.plot_benchmark_comparison(benchmark_data, result_dir)
        logger.info(
            f"All evaluation plots saved to {result_dir}.")

    def plot_cash_flow(self, result_dir: str) -> None:
        """
        Plot and save a stacked band plot of cash and total assets value.
        """
        plt.figure(figsize=(10, 6))

        # Ensure cash flow is calculated
        self.get_cash_flow()

        # Plot stacked band plot
        plt.fill_between(
            self.data.index,
            self.data["cash"],
            label="Cash",
            color="skyblue",
            alpha=0.7
        )
        plt.fill_between(
            self.data.index,
            self.data["total_assets"],
            self.data["cash"],
            label="Non-Cash Assets",
            color="lightgreen",
            alpha=0.7
        )

        # Add labels and title
        plt.title("Cash and Total Assets Composition")
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.legend(loc="upper left")
        plt.tight_layout()

        # Save the plot
        plt.savefig(f"{result_dir}/cash_flow.png")
        plt.close()

    def save_evaluation_results(self, result_dir: str) -> None:
        """
        Save evaluation results to a JSON file.
        """
        evaluation_results = {
            "ROI": float(self.get_roi()),
            "Total P&L": float(self.get_total_pnl()),
            "Sharpe Ratio": float(self.get_sharpe_ratio()),
            "Sortino Ratio": float(self.get_sortino_ratio()),
            "Calmar Ratio": float(self.get_calmar_ratio()),
            "Max Drawdown": float(self.get_max_drawdown()),
            "CAGR": float(self.get_cagr()),
            "Win Rate": float(self.get_win_rate()) if self.name != "vnindex" else None,
            "Expected Return": float(self.get_expected_return()) if self.name != "vnindex" else None,
            "Volatility": float(self.get_volatility()),
            "Max Time to Recover": int(self.get_max_time_to_recover()),
        }

        # Save the results to a JSON file
        with open(f"{result_dir}/{self.name}_evaluation.json", 'w') as f:
            json.dump(evaluation_results, f, indent=4)
        logger.info(
            f"Evaluation results saved to {result_dir}/{self.name}_evaluation.json")

    def evaluate(self, result_dir: str) -> None:
        """
        Evaluate the performance of the trading strategy.
        Save the evaluation results to a JSON file in the specified directory.
        Export plots to the specified directory.
        """
        plt.style.use(
            "seaborn-v0_8-darkgrid")  # Professional-looking dark grid style

        # Customizing color and aesthetics
        plt.rcParams.update({
            "axes.facecolor": "#F8F9FA",  # Light gray background
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#333333",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "grid.color": "#DDDDDD",
            "lines.linewidth": 2,
            "legend.frameon": False,
            "font.size": 12,
            "figure.figsize": (10, 6)
        })

        self.save_evaluation_results(result_dir)
        self.plot_all(benchmark_data=None, result_dir=result_dir)

    def quick_evaluate(self) -> Dict[str, Any]:
        """
        Quickly evaluate the performance of the trading strategy.
        Return the evaluation results as a dictionary.
        - ROI
        - Sharpe Ratio
        - Maximum Drawdown
        """
        evaluation_results = {
            "roi": float(self.get_roi()),
            "sharpe": float(self.get_sharpe_ratio()),
            "mdd": float(self.get_max_drawdown()),
        }
        return evaluation_results
