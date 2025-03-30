from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list
from src.market.simulation import MarketSimulation
from src.market.portfolio import Portfolio
from datetime import datetime
from src.utitlies import get_last_month
from src.settings import logger
import numpy as np


class Backtesting:
    def __init__(self, start_date: datetime, end_date: datetime, initial_balance: float):
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = Portfolio("Test Portfolio", initial_balance)
        self.simulation = MarketSimulation(start_date, end_date)
        self.realized_pl_values = [0.0]  # Track realized profit/loss over time
        self.delay = False
        self.stocks = get_stocks_list()

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
    def calculate_sharpe_ratio(realized_pl_values, risk_free_rate=0.0):
        returns = np.diff(realized_pl_values)
        excess_returns = returns - risk_free_rate
        if np.std(excess_returns) == 0:
            return 0.0
        return np.mean(excess_returns) / np.std(excess_returns)

    @staticmethod
    def calculate_maximum_drawdown(realized_pl_values):
        peak = -np.inf
        max_drawdown = 0
        for value in realized_pl_values:
            peak = max(peak, value)
            drawdown = (peak - value) / peak if peak != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown * 100

    def print_statistics(self):
        sharpe_ratio = self.calculate_sharpe_ratio(self.realized_pl_values)
        max_drawdown = self.calculate_maximum_drawdown(self.realized_pl_values)

        logger.info(f"Portfolio balance: {self.portfolio.balance}")
        logger.info(f"Realized P/L: {self.portfolio.realized_profit_loss}")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"Maximum Drawdown: {max_drawdown:.2f}%")

    def rebalance_portfolio(self):
        logger.info(
            f"Rebalancing portfolio on {self.simulation.current_date}.")
        last_month, last_year = get_last_month(
            self.simulation.current_date.month, self.simulation.current_date.year
        )
        ranked_stocks = StocksRanking(
            last_month, last_year, self.stocks).get_ranking()

        top_stocks = [symbol for symbol, _ in ranked_stocks[:5]]
        logger.info(f"Top 5 stocks for rebalancing: {top_stocks}")

        current_assets = list(self.portfolio.assets.keys())

        # Sell stocks that are no longer in the top stocks
        for asset in current_assets:
            if asset not in top_stocks:
                quantity = self.portfolio.assets[asset]['quantity']
                if not self.sell(asset, quantity):
                    self.delay = True
                    continue

        # Buy new stocks that are in the top stocks but not in the portfolio
        for symbol in top_stocks:
            if symbol not in current_assets:
                quantity = 10  # Example: Buy 10 shares of each new stock
                if not self.buy(symbol, quantity):
                    self.delay = True
                    continue

    def run(self):
        logger.info("Starting backtesting process.")
        while True:
            if not self.simulation.step():
                logger.info("Simulation completed.")
                break

            # Get the current stock data
            current_data = self.simulation.get_current_stock_data()
            if current_data.empty:
                logger.debug("No market data available for the current date.")
                continue

            # Track realized profit/loss
            self.realized_pl_values.append(self.portfolio.realized_profit_loss)

            # If the current month is the end_date, sell all stocks
            if (
                self.simulation.current_date.month == self.end_date.month
                and self.simulation.current_date.year == self.end_date.year
            ):
                logger.info(
                    "End of simulation period reached. Selling all stocks.")
                current_assets = list(self.portfolio.assets.keys())
                for asset in current_assets:
                    quantity = self.portfolio.assets[asset]['quantity']
                    if not self.sell(asset, quantity):
                        self.delay = True
                        continue
                logger.info("Final portfolio statistics:")
                self.print_statistics()
                break

            # Rebalance the portfolio on the 8th day of each month
            if self.simulation.current_date.day == 8 or self.delay:
                self.delay = False
                self.rebalance_portfolio()

            # Log the portfolio statistics
            logger.debug(
                f"Realized P/L so far: {self.portfolio.realized_profit_loss}")


if __name__ == '__main__':
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    initial_balance = 1000000

    backtesting = Backtesting(start_date, end_date, initial_balance)
    backtesting.run()
