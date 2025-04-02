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
from typing import List, Dict, Any
import argparse
import os
import json


class Backtesting:
    """
    A class to simulate and evaluate a stock trading strategy.
    """
    RELEASE_DAY = 20  # Day of the month when new data is released
    MAX_VOLUME = 20000  # Maximum volume of stocks to buy/sell in one transaction

    def __init__(self, start_date: datetime, end_date: datetime,
                 params: Dict[str, Any] = config["default_backtest_params"]):
        """
        Initialize the backtesting environment.

        :param start_date: Start date of the simulation.
        :param end_date: End date of the simulation.
        :param initial_balance: Initial cash balance for the portfolio.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = Portfolio("Test Portfolio", params["initial_balance"])
        self.NUMBER_OF_STOCKS = params.get(
            "number_of_stocks", 3)
        self.TRAILING_STOP_LOSS = params.get(
            "trailing_stop_loss", 0.35)
        self.TAKE_PROFIT = params.get(
            "take_profit", 0.25)
        self.WEIGHTING_OPTION = params.get(
            "stock_weight_option", "softmax")
        self.params = params
        self.simulation = MarketSimulation(start_date, end_date)
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
            asset, quantity, sell_info['total_revenue'], sell_info['price'], sell_info['date']
        )
        logger.debug(
            f"{self.simulation.current_date.date()} "
            f"Sold {quantity} shares of {asset} at {sell_info['price']} each. Realized P/L: {realized_pl:.2f}"
        )
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
            symbol, quantity, buy_info['total_cost'], buy_info['price'], buy_info['date']
        )
        logger.debug(
            f"{self.simulation.current_date.date()} "
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
        ranked_stocks = StocksRanking(self.simulation.current_date.month,
                                      self.simulation.current_date.year,
                                      self.stocks,
                                      self.params).get_ranking()
        self.top_stocks = [symbol for symbol,
                           _ in ranked_stocks[:self.NUMBER_OF_STOCKS]]
        logger.info(
            f"{self.simulation.current_date.date()} "
            f"Top {self.NUMBER_OF_STOCKS} stocks for rebalancing: "
            f"{self.top_stocks}")

        # Sell stocks not in the top stocks
        for asset in list(self.portfolio.assets.keys()):
            if asset not in self.top_stocks:
                self.sell(asset, self.portfolio.assets[asset]['quantity'])

        # Allocate 90% of the portfolio balance for buying stocks
        available_balance = self.portfolio.balance * 0.9
        weights = self.get_weights(
            ranked_stocks, self.WEIGHTING_OPTION)

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

    def check_sell_conditions(self, asset: str, current_price: float) -> bool:
        """
        Check if the asset should be sold based on trailing stop loss or take profit conditions.

        :param asset: Stock symbol to check.
        :param current_price: Current price of the asset.
        :return: True if the asset should be sold, False otherwise.
        """
        asset_data = self.portfolio.assets.get(asset, {})
        if not asset_data:
            return False

        purchase_price = asset_data['average_price']

        # Update the peak price for the asset
        self.peak_prices[asset] = max(self.peak_prices.get(
            asset, current_price), current_price)

        # Check take profit condition
        if (current_price - purchase_price) / purchase_price >= self.TAKE_PROFIT:
            logger.info(
                f"{self.simulation.current_date.date()} "
                f"Take profit triggered for {asset}. Current price: {current_price}")
            return True

        # Check trailing stop loss condition
        peak_price = self.peak_prices[asset]
        if (current_price - peak_price) / peak_price <= -self.TRAILING_STOP_LOSS:
            logger.info(
                f"{self.simulation.current_date.date()} "
                f"Trailing stop loss triggered for {asset}. Current price: {current_price}")
            return True

        return False

    def run(self):
        """
        Run the backtesting simulation.
        """
        logger.info("Starting backtesting process.")
        start_time = time.time()
        last_month = self.simulation.current_date.month

        while self.simulation.step():
            current_date = self.simulation.current_date
            if current_date.month != last_month:
                last_month = current_date.month
                self.need_rebalance = True

            items = list(self.portfolio.assets.items())
            is_last_trading_day = self.simulation.is_last_trading_day()
            if is_last_trading_day:
                logger.info(
                    f"{current_date.date()} "
                    f"Last trading day, sell all assets"
                    f" in the portfolio: {', '.join(self.portfolio.assets.keys())}"
                )

            if (not is_last_trading_day
                and current_date.day >= self.RELEASE_DAY
                    and self.need_rebalance):
                # Rebalance portfolio
                self.rebalance_portfolio()

            # Check sell conditions for each asset
            for asset, asset_data in items:
                current_price = self.simulation.get_last_available_price(asset)
                if (is_last_trading_day
                    or (current_price > 0
                        and self.check_sell_conditions(asset, current_price))):
                    self.sell(asset, asset_data['quantity'])

            # # Retrieve daily statistics from the portfolio
            daily_stats = self.portfolio.get_daily_statistics(
                current_date)
            portfolio_stats = self.simulation.get_portfolio_statistics(
                self.portfolio)

            # # Append daily statistics to portfolio_statistics
            self.portfolio_statistics.append({
                "datetime": current_date,
                "total_assets": portfolio_stats['total_value'],
                "cash": self.portfolio.balance,
                "number_of_trades": daily_stats['number_of_trades'],
                "number_of_winners": daily_stats['number_of_winners'],
                "sum_of_winners": daily_stats['sum_of_winners'],
                "sum_of_losers": daily_stats['sum_of_losers'],
            })

        runtime = time.time() - start_time
        logger.debug(f"Backtesting completed in {runtime:.2f} seconds.")

    def evaluate(self, result_dir: str):
        """
        Evaluate the backtesting results using the Evaluate class.

        :param result_dir: Directory to save evaluation results.
        """
        evaluation_data = pd.DataFrame(self.portfolio_statistics)
        evaluator = Evaluate(evaluation_data, name="backtest")
        evaluator.evaluate(result_dir)

    def save_portfolio(self, result_dir: str):
        """
        Save the portfolio statistics to a CSV file.

        :param result_dir: Directory to save portfolio statistics.
        """
        portfolio_df = pd.DataFrame(self.portfolio_statistics)
        portfolio_df.to_csv(os.path.join(result_dir, "portfolio.csv"),
                            index=False)
        logger.info(
            f"Portfolio statistics saved to {result_dir}/portfolio.csv")

        transaction_history = self.portfolio.transactions
        transaction_df = pd.DataFrame(transaction_history)
        transaction_df['datetime'] = pd.to_datetime(
            transaction_df['datetime']).dt.strftime('%Y-%m-%d')
        transaction_df.set_index('datetime', inplace=True)
        transaction_df.sort_index(inplace=True)
        transaction_df.to_csv(os.path.join(result_dir, "transactions.csv"),
                              index=False)
        logger.info(
            f"Transaction history saved to {result_dir}/transactions.csv")

        # save params to JSON file
        params_file = os.path.join(result_dir, "params.json")
        with open(params_file, 'w') as f:
            json.dump(self.params, f, indent=4)
        logger.info(f"Parameters saved to {params_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backtesting script")
    parser.add_argument("--start_date", type=str, required=True,
                        help="Start date for backtesting (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, required=True,
                        help="End date for backtesting (YYYY-MM-DD)")
    parser.add_argument("--disable_logging", action="store_true",
                        default=False,
                        help="Disable logging during backtesting")
    parser.add_argument("--name", type=str, required=True,
                        help="Name for the backtest")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

    assert end_date.day >= 20, "End date must be after the 20th of the month."

    backtesting = Backtesting(start_date, end_date)
    backtesting.run()
    result_dir = f"{DATA_PATH}/backtest/{args.name}"
    os.makedirs(result_dir, exist_ok=True)
    backtesting.evaluate(result_dir=result_dir)
    backtesting.save_portfolio(result_dir=result_dir)
