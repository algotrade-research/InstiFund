from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list
from src.market.simulation import MarketSimulation
from src.market.portfolio import Portfolio
from src.evaluate import Evaluate
from datetime import datetime
from src.settings import logger, DATA_PATH, config
import numpy as np
import pandas as pd
import time
from typing import List, Dict


class Backtesting:
    """
    A class to simulate and evaluate a stock trading strategy.
    """
    RELEASE_DAY = 20  # Day of the month when new data is released
    MAX_VOLUME = 20000  # Maximum volume of stocks to buy/sell in one transaction
    NUMBER_OF_STOCKS = 3  # Number of stocks to keep in the portfolio
    TRAILING_STOP_LOSS = 0.5  # 50% loss threshold to trigger a sell
    TAKE_PROFIT = 0.25  # 25% profit threshold to trigger a sell

    def __init__(self, start_date: datetime, end_date: datetime, initial_balance: float):
        """
        Initialize the backtesting environment.

        :param start_date: Start date of the simulation.
        :param end_date: End date of the simulation.
        :param initial_balance: Initial cash balance for the portfolio.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = Portfolio("Test Portfolio", initial_balance)
        self.simulation = MarketSimulation(start_date, end_date)
        self.trading_days = []  # Track trading days
        self.stocks = get_stocks_list()  # List of available stocks
        self.top_stocks = []  # Top stocks for rebalancing
        self.need_rebalance = True  # Flag to indicate if rebalancing is needed
        self.peak_prices = {}  # Track the peak price of each stock in the portfolio
        self.portfolio_statistics = []  # Store portfolio statistics for evaluation

    def sell(self, asset: str, quantity: int) -> bool:
        """
        Sell a specified quantity of a stock.

        :param asset: Stock symbol to sell.
        :param quantity: Number of shares to sell.
        :return: True if the sell was successful, False otherwise.
        """
        sell_info = self.simulation.sell_stock(asset, quantity)
        if not sell_info.get('total_revenue'):
            logger.warning(f"Failed to sell {quantity} shares of {asset}.")
            return False

        realized_pl = sell_info['total_revenue'] - \
            self.portfolio.paid_value(asset, quantity)
        self.portfolio.remove_asset(
            asset, quantity, sell_info['total_revenue'], sell_info['price'], sell_info['date'])
        logger.debug(
            f"Sold {quantity} shares of {asset} at {sell_info['price']} each. Realized P/L: {realized_pl:.2f}")
        return True

    def buy(self, symbol: str, quantity: int) -> bool:
        """
        Buy a specified quantity of a stock.

        :param symbol: Stock symbol to buy.
        :param quantity: Number of shares to buy.
        :return: True if the buy was successful, False otherwise.
        """
        buy_info = self.simulation.buy_stock(symbol, quantity)
        if not buy_info.get('total_cost'):
            logger.warning(f"Failed to buy {quantity} shares of {symbol}.")
            return False

        self.portfolio.add_asset(
            symbol, quantity, buy_info['total_cost'], buy_info['price'], buy_info['date'])
        logger.debug(
            f"Bought {quantity} shares of {symbol} at {buy_info['price']} each.")
        return True

    def is_matched_top_stocks(self) -> bool:
        """
        Check if the current portfolio matches the top stocks.

        :return: True if the portfolio matches the top stocks, False otherwise.
        """
        return sorted(self.portfolio.assets.keys()) == sorted(self.top_stocks)

    def get_weights(self, ranked_stocks: List, option: str) -> Dict[str, float]:
        """
        Get the weights for the top stocks based on their scores.

        :param ranked_stocks: List of ranked stocks with their scores.
        :param option: Weighting option ('softmax', 'equal', or 'linear').
        :return: Dictionary of stock symbols and their corresponding weights.
        """
        scores = [score for _, score in ranked_stocks[:self.NUMBER_OF_STOCKS]]
        if option == 'softmax':
            exp_scores = np.exp(scores)
            weights = exp_scores / np.sum(exp_scores)
        elif option == 'equal':
            weights = np.ones(len(scores)) / len(scores)
        elif option == 'linear':
            weights = np.array(scores) / np.sum(scores)
        else:
            raise ValueError(
                "Invalid option. Choose 'softmax', 'equal', or 'linear'.")

        return {symbol: weight for (symbol, _), weight in zip(ranked_stocks[:self.NUMBER_OF_STOCKS], weights)}

    def rebalance_portfolio(self):
        """
        Rebalance the portfolio based on the top-ranked stocks.
        """
        logger.info(
            f"Date: {self.simulation.current_date.strftime('%Y-%m-%d')} - Rebalancing portfolio.")
        ranked_stocks = StocksRanking(self.simulation.current_date.month,
                                      self.simulation.current_date.year, self.stocks).get_ranking()
        self.top_stocks = [symbol for symbol,
                           _ in ranked_stocks[:self.NUMBER_OF_STOCKS]]
        logger.info(
            f"Top {self.NUMBER_OF_STOCKS} stocks for rebalancing: {ranked_stocks[:self.NUMBER_OF_STOCKS]}")

        # Sell stocks not in the top stocks
        for asset in list(self.portfolio.assets.keys()):
            if asset not in self.top_stocks:
                self.sell(asset, self.portfolio.assets[asset]['quantity'])

        # Allocate 90% of the portfolio balance for buying stocks
        available_balance = self.portfolio.balance * 0.9
        weights = self.get_weights(ranked_stocks, 'linear')

        # Buy or adjust holdings for the top stocks
        for symbol in self.top_stocks:
            stock_price = self.simulation.get_last_available_price(
                symbol) * 1.01
            if not stock_price or stock_price <= 0:
                logger.warning(f"Failed to get price for {symbol}. Skipping.")
                continue

            allocated_funds = available_balance * weights[symbol]
            desired_quantity = min(
                int(allocated_funds // stock_price), self.MAX_VOLUME)
            current_quantity = self.portfolio.assets.get(
                symbol, {}).get('quantity', 0)

            if desired_quantity > current_quantity:
                self.buy(symbol, desired_quantity - current_quantity)
            elif desired_quantity < current_quantity:
                self.sell(symbol, current_quantity - desired_quantity)

        if self.is_matched_top_stocks():
            self.need_rebalance = False

    def update_peak_price(self, asset, current_price):
        """
        Update the peak price for a given asset.
        """
        if asset not in self.peak_prices:
            self.peak_prices[asset] = current_price
        else:
            self.peak_prices[asset] = max(
                self.peak_prices[asset], current_price)

    def check_sell_conditions(self, asset):
        """
        Check if the asset should be sold based on trailing stop loss or take profit conditions.
        """
        asset_data = self.portfolio.assets.get(asset, {})
        if not asset_data:
            return False

        purchase_price = asset_data['average_price']
        current_price = self.simulation.get_last_available_price(asset)

        if current_price is None or current_price <= 0:
            logger.warning(
                f"Failed to get current price for {asset}. Skipping sell condition check.")
            return False

        # Update the peak price for the asset
        self.update_peak_price(asset, current_price)

        # Calculate percentage change from purchase price
        price_change = (current_price - purchase_price) / purchase_price

        # Check take profit condition
        if price_change >= self.TAKE_PROFIT:
            logger.debug(
                f"Take profit triggered for {asset}. Current price: {current_price}, Purchase price: {purchase_price}")
            return True

        # Check trailing stop loss condition
        peak_price = self.peak_prices.get(asset, current_price)
        if (current_price - peak_price) / peak_price <= -self.TRAILING_STOP_LOSS:
            logger.debug(
                f"Trailing stop loss triggered for {asset}. Current price: {current_price}, Peak price: {peak_price}")
            # self.need_rebalance = True
            return True

        return False

    def run(self, disable_logging: bool = False):
        """
        Run the backtesting simulation.

        :param disable_logging: Disable logging for performance.
        """
        logger.disabled = disable_logging
        logger.info("Starting backtesting process.")
        start_time = time.time()
        last_month = self.simulation.current_date.month

        while self.simulation.step():
            if self.simulation.current_date.month != last_month:
                last_month = self.simulation.current_date.month
                self.need_rebalance = True

            # Calculate daily return
            portfolio_statistics = self.simulation.get_portfolio_statistics(
                self.portfolio)
            current_total_value = portfolio_statistics['total_value']
            self.portfolio_statistics.append({
                "datetime": self.simulation.current_date,
                "total_assets": current_total_value,
                "cash": self.portfolio.balance,
                "number_of_trades": len(self.portfolio.transactions),
                "number_of_winners": sum(1 for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] > 0),
                "sum_of_winners": sum(t['realized_pl'] for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] > 0),
                "sum_of_losers": sum(t['realized_pl'] for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] < 0),
            })

            self.trading_days.append(
                self.simulation.current_date.strftime("%Y-%m-%d"))

            # Check sell conditions for each asset
            for asset in list(self.portfolio.assets.keys()):
                if self.check_sell_conditions(asset):
                    self.sell(asset, self.portfolio.assets[asset]['quantity'])

            # End simulation if it's the last month
            if (self.simulation.current_date.month == self.end_date.month and
                self.simulation.current_date.year == self.end_date.year and
                    self.simulation.current_date.day >= self.RELEASE_DAY):
                for asset in list(self.portfolio.assets.keys()):
                    self.sell(asset, self.portfolio.assets[asset]['quantity'])
                break

            # Rebalance portfolio
            if self.simulation.current_date.day >= self.RELEASE_DAY and self.need_rebalance:
                self.rebalance_portfolio()

        logger.disabled = config.get("disable_logging", False)
        runtime = time.time() - start_time
        logger.info(
            f"Backtesting completed in {runtime:.2f} seconds.")

    def evaluate(self, result_dir: str):
        """
        Evaluate the backtesting results using the Evaluate class.

        :param result_dir: Directory to save evaluation results.
        """
        evaluation_data = pd.DataFrame(self.portfolio_statistics)
        evaluator = Evaluate(evaluation_data, name="backtest")
        evaluator.evaluate(result_dir)


if __name__ == '__main__':
    start_date = datetime(2023, 2, 1)
    end_date = datetime(2024, 1, 31)  # The day must be >= 20
    initial_balance = 1000000

    backtesting = Backtesting(start_date, end_date, initial_balance)
    backtesting.run()
    backtesting.evaluate(result_dir=DATA_PATH)
