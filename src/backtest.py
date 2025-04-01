from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list
from src.market.simulation import MarketSimulation
from src.market.portfolio import Portfolio
from src.evaluate import Evaluate
from datetime import datetime
from src.settings import logger, DATA_PATH
import numpy as np
import pandas as pd
from typing import List, Dict


class Backtesting:
    RELEASE_DAY = 20  # Day of the month that new data is released
    MAX_VOLUME = 20000  # Maximum volume of stocks to buy/sell in one transaction
    NUMBER_OF_STOCKS = 3  # Number of stocks to keep in the portfolio
    TRAILING_STOP_LOSS = 0.5  # 10% loss threshold to trigger a sell
    TAKE_PROFIT = 0.25  # 20% profit threshold to trigger a sell

    def __init__(self, start_date: datetime, end_date: datetime, initial_balance: float):
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = Portfolio("Test Portfolio", initial_balance)
        self.simulation = MarketSimulation(start_date, end_date)
        self.daily_returns = []  # Track portfolio daily returns
        self.trading_days = []
        self.stocks = get_stocks_list()
        self.previous_total_value = initial_balance
        self.top_stocks = []  # Top stocks for rebalancing
        self.need_rebalance = True
        self.peak_prices = {}  # Track the peak price of each stock in the portfolio
        self.portfolio_statistics = []  # Store portfolio statistics for evaluation

    def sell(self, asset, quantity):
        sell_info = self.simulation.sell_stock(asset, quantity)
        if sell_info.get('total_revenue') is None:
            logger.warning(f"Failed to sell {quantity} shares of {asset}.")
            return False
        realized_pl = sell_info['total_revenue'] - \
            self.portfolio.paid_value(asset, quantity)
        self.portfolio.remove_asset(
            asset, quantity, sell_info['total_revenue'], sell_info['price'],
            sell_info['date']
        )
        logger.info(
            f"Sold {quantity} shares of {asset} at {sell_info['price']} each."
            f" Realized P/L: {realized_pl:.2f}")
        return True

    def buy(self, symbol, quantity):
        buy_info = self.simulation.buy_stock(symbol, quantity)
        if buy_info.get('total_cost') is None:
            logger.warning(f"Failed to buy {quantity} shares of {symbol}.")
            return False
        self.portfolio.add_asset(
            symbol, quantity, buy_info['total_cost'], buy_info['price'], buy_info['date']
        )
        logger.info(
            f"Bought {quantity} shares of {symbol} at {buy_info['price']} each.")
        return True

    def is_matched_top_stocks(self) -> bool:
        """
        Check if the current portfolio matches the top stocks.
        """
        current_assets = list(self.portfolio.assets.keys())
        return sorted(current_assets) == sorted(self.top_stocks)

    def get_weights(self, ranked_stocks: List, option: str) -> Dict[str, float]:
        """
        Get the weights for the top stocks based on their scores.
        :param option: 'softmax', 'equal', or 'linear'.
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

        return {symbol: weight for (symbol, _), weight in zip(
            ranked_stocks[:self.NUMBER_OF_STOCKS], weights)}

    def rebalance_portfolio(self):
        logger.info(
            f"Date: {self.simulation.current_date.strftime('%Y-%m-%d')} - Rebalancing portfolio.")
        ranked_stocks = StocksRanking(
            self.simulation.current_date.month,
            self.simulation.current_date.year,
            self.stocks).get_ranking()

        self.top_stocks = [symbol for symbol,
                           _ in ranked_stocks[:self.NUMBER_OF_STOCKS]]
        logger.info(
            f"Top {self.NUMBER_OF_STOCKS} stocks for rebalancing: {ranked_stocks[:self.NUMBER_OF_STOCKS]}")

        current_assets = list(self.portfolio.assets.keys())

        # Sell stocks that are no longer in the top stocks
        for asset in current_assets:
            if asset not in self.top_stocks:
                quantity = self.portfolio.assets[asset]['quantity']
                if quantity > 0:
                    self.sell(asset, quantity)

        # Calculate 90% of the portfolio balance for buying stocks
        available_balance = self.portfolio.balance * 0.9

        # Calculate weights for the top stocks
        weights = self.get_weights(ranked_stocks, 'linear')

        # Buy or adjust holdings for the top stocks
        for symbol in self.top_stocks:
            stock_price = self.simulation.get_last_day_stock_price(
                symbol) * 1.01
            if stock_price is None or stock_price <= 0:
                logger.warning(f"Failed to get price for {symbol}. Skipping.")
                continue

            # Allocate funds based on softmax weight
            allocated_funds = available_balance * weights[symbol]
            desired_quantity = min(
                int(allocated_funds // stock_price), self.MAX_VOLUME)

            # Adjust holdings to match the desired quantity
            current_quantity = self.portfolio.assets.get(
                symbol, {}).get('quantity', 0)
            if desired_quantity > current_quantity:
                self.buy(symbol, min(desired_quantity -
                         current_quantity, self.MAX_VOLUME))
            elif desired_quantity < current_quantity:
                self.sell(symbol, min(current_quantity -
                          desired_quantity, self.MAX_VOLUME))

        # Update the need_rebalance flag
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
        current_price = self.simulation.get_last_day_stock_price(asset)

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
            logger.info(
                f"Take profit triggered for {asset}. Current price: {current_price}, Purchase price: {purchase_price}")
            return True

        # Check trailing stop loss condition
        peak_price = self.peak_prices.get(asset, current_price)
        if (current_price - peak_price) / peak_price <= -self.TRAILING_STOP_LOSS:
            logger.info(
                f"Trailing stop loss triggered for {asset}. Current price: {current_price}, Peak price: {peak_price}")
            self.need_rebalance = True
            return True

        return False

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
            daily_return = (
                current_total_value - self.previous_total_value) / self.previous_total_value
            self.daily_returns.append(daily_return)
            self.portfolio_statistics.append({
                "datetime": self.simulation.current_date,
                "total_assets": current_total_value,
                "cash": self.portfolio.balance,
                "number_of_trades": len(self.portfolio.transactions),
                "number_of_winners": sum(1 for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] > 0),
                "sum_of_winners": sum(t['realized_pl'] for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] > 0),
                "sum_of_losers": sum(t['realized_pl'] for t in self.portfolio.transactions if t['action'] == 'sell' and t['realized_pl'] < 0),
            })

            self.previous_total_value = current_total_value
            self.trading_days.append(
                self.simulation.current_date.strftime("%Y-%m-%d"))

            # Check sell conditions for each asset in the portfolio
            current_assets = list(self.portfolio.assets.keys())
            for asset in current_assets:
                if self.check_sell_conditions(asset):
                    quantity = self.portfolio.assets[asset]['quantity']
                    self.sell(asset, quantity)

            # If the current month is the end_date, sell all stocks
            if (
                self.simulation.current_date.month == self.end_date.month
                and self.simulation.current_date.year == self.end_date.year
                and self.simulation.current_date.day >= self.RELEASE_DAY
            ):
                logger.info(
                    f"Date: {self.simulation.current_date.strftime('%Y-%m-%d')}")
                logger.info(
                    "End of simulation period reached. Selling all stocks.")
                for asset in current_assets:
                    quantity = self.portfolio.assets[asset]['quantity']
                    self.sell(asset, quantity)
                break

            # Rebalance the portfolio on the 8th day of each month
            if self.simulation.current_date.day >= self.RELEASE_DAY\
                    and self.need_rebalance:
                self.rebalance_portfolio()

    def evaluate(self, result_dir: str):
        """
        Evaluate the backtesting results using the Evaluate class.
        """
        evaluation_data = pd.DataFrame(self.portfolio_statistics)
        evaluator = Evaluate(evaluation_data, name="backtest")
        evaluator.evaluate(result_dir)


if __name__ == '__main__':
    start_date = datetime(2023, 2, 1)
    end_date = datetime(2024, 1, 31)  # the day must be >= 20
    initial_balance = 1000000

    backtesting = Backtesting(start_date, end_date, initial_balance)
    backtesting.run()
    backtesting.evaluate(result_dir=DATA_PATH)
