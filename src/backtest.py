from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list
from src.market.simulation import MarketSimulation
from src.market.portfolio import Portfolio
from datetime import datetime
from src.utitlies import get_last_month
from src.settings import logger, DATA_PATH
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class Backtesting:
    def __init__(self, start_date: datetime, end_date: datetime, initial_balance: float):
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = Portfolio("Test Portfolio", initial_balance)
        self.simulation = MarketSimulation(start_date, end_date)
        self.daily_returns = []  # Track portfolio daily returns
        self.trading_days = []
        self.stocks = get_stocks_list()
        # Track the previous day's total portfolio value
        self.previous_total_value = initial_balance
        self.top_stocks = []  # Top stocks for rebalancing
        self.need_rebalance = True

    def sell(self, asset, quantity):
        sell_info = self.simulation.sell_stock(asset, quantity)
        if sell_info.get('total_revenue') is None:
            logger.warning(f"Failed to sell {asset}.")
            return False
        self.portfolio.remove_asset(
            asset, quantity, sell_info['total_revenue'], sell_info['price'], sell_info['date']
        )
        logger.info(
            f"Sold {quantity} shares of {asset} at {sell_info['price']} each.")
        return True

    def buy(self, symbol, quantity):
        buy_info = self.simulation.buy_stock(symbol, quantity)
        if buy_info.get('total_cost') is None:
            logger.warning(f"Failed to buy {symbol}.")
            return False
        self.portfolio.add_asset(
            symbol, quantity, buy_info['total_cost'], buy_info['price'], buy_info['date']
        )
        logger.info(
            f"Bought {quantity} shares of {symbol} at {buy_info['price']} each.")
        return True

    @staticmethod
    def calculate_sharpe_ratio(daily_returns, risk_free_rate_annually=0.045):
        """
        Calculate the Sharpe ratio based on daily returns.
        :param daily_returns: List of daily returns.
        :param risk_free_rate: Risk-free rate (default is 0.0045 -- Vietnamese bank interest rate).
        :return: Sharpe ratio.
        """
        risk_free_rate_daily = risk_free_rate_annually / 252
        excess_returns = np.array(daily_returns) - risk_free_rate_daily
        if np.std(excess_returns) == 0:
            return 0.0
        return np.mean(excess_returns) / np.std(excess_returns, ddof=1) * np.sqrt(252)

    @staticmethod
    def calculate_maximum_drawdown(daily_returns):
        """
        Calculate the maximum drawdown based on daily returns.
        :param daily_returns: List of daily returns.
        :return: Maximum drawdown as a percentage.
        """
        cumulative_returns = np.cumprod(1 + np.array(daily_returns)) - 1
        peak = -np.inf
        max_drawdown = 0
        for value in cumulative_returns:
            peak = max(peak, value)
            drawdown = (peak - value) / (peak + 1) if peak != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown * 100

    def print_statistics(self):
        sharpe_ratio = self.calculate_sharpe_ratio(self.daily_returns)
        max_drawdown = self.calculate_maximum_drawdown(self.daily_returns)

        logger.info(f"Portfolio balance: {self.portfolio.balance}")
        logger.info(f"Realized P/L: {self.portfolio.realized_profit_loss}")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"Maximum Drawdown: {max_drawdown:.2f}%")

    def is_matched_top_stocks(self) -> bool:
        """
        Check if the current portfolio matches the top stocks.
        """
        current_assets = list(self.portfolio.assets.keys())
        return sorted(current_assets) == sorted(self.top_stocks)

    def rebalance_portfolio(self):
        logger.info(
            f"Date: {self.simulation.current_date.strftime('%Y-%m-%d')}")
        logger.info(
            f"Rebalancing portfolio on {self.simulation.current_date}.")
        last_month, last_year = get_last_month(
            self.simulation.current_date.month, self.simulation.current_date.year
        )
        ranked_stocks = StocksRanking(
            last_month, last_year, self.stocks).get_ranking()

        self.top_stocks = [symbol for symbol, _ in ranked_stocks[:3]]
        logger.info(f"Top 3 stocks for rebalancing: {self.top_stocks}")

        current_assets = list(self.portfolio.assets.keys())

        # Sell stocks that are no longer in the top stocks
        for asset in current_assets:
            if asset not in self.top_stocks:
                quantity = self.portfolio.assets[asset]['quantity']
                self.sell(asset, quantity)

        # Buy new stocks that are in the top stocks but not in the portfolio
        for symbol in self.top_stocks:
            if symbol not in current_assets:
                quantity = 200  # Example: Buy 200 shares of each new stock
                self.buy(symbol, quantity)

        # Update the need_rebalance flag
        if self.is_matched_top_stocks():
            self.need_rebalance = False

    def run(self):
        logger.info("Starting backtesting process.")
        last_month = self.simulation.current_date.month
        while True:
            if not self.simulation.step():
                logger.info("Simulation completed.")
                break
            if self.simulation.current_date.month != last_month:
                last_month = self.simulation.current_date.month
                self.need_rebalance = True

            # Calculate daily return
            portfolio_statistics = self.simulation.get_portfolio_statistics(
                self.portfolio)
            current_total_value = portfolio_statistics['total_value']
            # logger.info(f"Current portfolio value: {current_total_value:.2f}")
            daily_return = (
                current_total_value - self.previous_total_value) / self.previous_total_value
            self.daily_returns.append(daily_return)
            if daily_return > 0.01:
                logger.warning(
                    f"Daily return is too high: {daily_return:.4f}. "
                    f"Previous value: {self.previous_total_value:.2f},"
                    f" Current value: {current_total_value:.2f}")

            self.previous_total_value = current_total_value
            self.trading_days.append(
                self.simulation.current_date.strftime("%Y-%m-%d"))

            # If the current month is the end_date, sell all stocks
            if (
                self.simulation.current_date.month == self.end_date.month
                and self.simulation.current_date.year == self.end_date.year
                and self.simulation.current_date.day >= 8
            ):
                logger.info(
                    "End of simulation period reached. Selling all stocks.")
                current_assets = list(self.portfolio.assets.keys())
                for asset in current_assets:
                    quantity = self.portfolio.assets[asset]['quantity']
                    self.sell(asset, quantity)
                logger.info("Final portfolio statistics:")
                self.print_statistics()
                break

            # Rebalance the portfolio on the 8th day of each month
            if self.simulation.current_date.day >= 8 and self.need_rebalance:
                self.rebalance_portfolio()

            # Log the portfolio statistics
            # logger.debug(
                # f"Realized P/L so far: {self.portfolio.realized_profit_loss}")

    def save_results(self, file_path: str = DATA_PATH + "/backtest_results.csv"):
        """
        Save the daily returns to a CSV file.
        """
        if not self.daily_returns:
            logger.warning("No daily returns to save.")
            return
        df = pd.DataFrame({
            'Date': self.trading_days,
            'Daily Return': self.daily_returns
        })
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1
        df.to_csv(file_path, index=False)
        # Export plot by Date
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Cumulative Return'], label='Cumulative Return')
        plt.title('Cumulative Return Over Time')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.tight_layout()
        plt.legend()
        plt.grid()
        plt.savefig(file_path.replace('.csv', '.png'))
        plt.close()
        # Export plot by Daily Return
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Daily Return'], label='Daily Return')
        plt.title('Daily Return Over Time')
        plt.xlabel('Date')
        plt.ylabel('Daily Return')
        plt.tight_layout()
        plt.legend()
        plt.grid()
        plt.savefig(file_path.replace('.csv', '_daily.png'))
        plt.close()

        logger.info(f"Daily returns saved to {file_path}.")


if __name__ == '__main__':
    start_date = datetime(2023, 2, 1)
    end_date = datetime(2024, 12, 31)
    initial_balance = 1000000

    backtesting = Backtesting(start_date, end_date, initial_balance)
    backtesting.run()
    backtesting.save_results()
