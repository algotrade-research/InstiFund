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
from vnstock import Vnstock


class Backtesting:
    RELEASE_DAY = 20  # Day of the month that new data is released
    MAX_VOLUME = 20000  # Maximum volume of stocks to buy/sell in one transaction
    NUMBER_OF_STOCKS = 5  # Number of stocks to keep in the portfolio
    TRAILING_STOP_LOSS = 0.30  # 10% loss threshold to trigger a sell
    TAKE_PROFIT = 0.28  # 20% profit threshold to trigger a sell

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
        self.peak_prices = {}  # Track the peak price of each stock in the portfolio

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
        # Calculate cumulative return
        cumulative_return = (1 + np.array(self.daily_returns)).prod() - 1

        logger.info(f"Portfolio balance: {self.portfolio.balance}")
        logger.info(f"Realized P/L: {self.portfolio.realized_profit_loss}")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"Maximum Drawdown: {max_drawdown:.2f}%")
        # Log cumulative return
        logger.info(f"Cumulative Return: {cumulative_return:.2f}%")

    def is_matched_top_stocks(self) -> bool:
        """
        Check if the current portfolio matches the top stocks.
        """
        current_assets = list(self.portfolio.assets.keys())
        return sorted(current_assets) == sorted(self.top_stocks)

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

        # Get scores for the top stocks and apply softmax to calculate weights
        scores = np.array(
            [score for _, score in ranked_stocks[:self.NUMBER_OF_STOCKS]])
        softmax_weights = np.exp(scores) / np.sum(np.exp(scores))
        weights = {symbol: weight for (symbol, _), weight in zip(
            ranked_stocks[:self.NUMBER_OF_STOCKS], softmax_weights)}

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
                self.print_statistics()
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
            if daily_return > 0.1:
                logger.warning(
                    f"Daily return is too high: {daily_return:.4f}. "
                    f"Previous value: {self.previous_total_value:.2f},"
                    f" Current value: {current_total_value:.2f}")

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
                logger.info("Final portfolio statistics:")
                self.print_statistics()
                break

            # Rebalance the portfolio on the 8th day of each month
            if self.simulation.current_date.day >= self.RELEASE_DAY\
                    and self.need_rebalance:
                self.rebalance_portfolio()

            # Log the portfolio statistics
            # logger.debug(
                # f"Realized P/L so far: {self.portfolio.realized_profit_loss}")

    def save_results(self, file_path: str = DATA_PATH + "/backtest_results.csv"):
        """
        Save the daily returns, cumulative returns, VNINDEX data, and maximum drawdown plot to files.
        """
        if not self.daily_returns:
            logger.warning("No daily returns to save.")
            return

        # Create a DataFrame for portfolio returns
        df = pd.DataFrame({
            'Date': self.trading_days,
            'Daily Return': self.daily_returns
        })
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1

        # Add VNINDEX data
        vnindex = Vnstock().stock(symbol="ACB", source="VCI")
        vnindex_hist = vnindex.quote.history(symbol="VNINDEX",
                                             start=self.start_date.strftime(
                                                 "%Y-%m-%d"),
                                             end=self.end_date.strftime(
                                                 "%Y-%m-%d"),
                                             interval="1D")
        vnindex_hist = vnindex_hist.rename(
            columns={"close": "VNINDEX"}).reset_index()
        vnindex_hist['Date'] = pd.to_datetime(vnindex_hist['time'])
        vnindex_hist.set_index('Date', inplace=True)
        vnindex_hist = vnindex_hist.reindex(df.index, method='ffill')
        df['VNINDEX'] = vnindex_hist['VNINDEX']
        df['VNINDEX Daily Return'] = df['VNINDEX'].pct_change()
        df['VNINDEX Cumulative Return'] = (
            1 + df['VNINDEX Daily Return']).cumprod() - 1

        # Save the results to a CSV file
        df.to_csv(file_path, index=True)

        # Export cumulative return plot with VNINDEX
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Cumulative Return'],
                 label='Portfolio Cumulative Return')
        plt.plot(df.index, df['VNINDEX Cumulative Return'],
                 label='VNINDEX Cumulative Return', linestyle='--')
        plt.title('Cumulative Return vs VNINDEX')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig(file_path.replace('.csv', '_cumulative_return.png'))
        plt.close()

        # Export maximum drawdown plot
        max_drawdown = self.calculate_maximum_drawdown(self.daily_returns)
        cumulative_returns = (1 + np.array(self.daily_returns)).cumprod() - 1
        drawdowns = [(peak - value) / (peak + 1) if peak != 0 else 0
                     for peak, value in
                     zip(np.maximum.accumulate(cumulative_returns),
                         cumulative_returns)]
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, drawdowns, label='Drawdown')
        plt.title(f'Maximum Drawdown: {max_drawdown:.2f}%')
        plt.xlabel('Date')
        plt.ylabel('Drawdown')
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig(file_path.replace('.csv', '_max_drawdown.png'))
        plt.close()

        logger.info(
            f"Results saved to {file_path} and associated plots exported.")


if __name__ == '__main__':
    start_date = datetime(2023, 2, 1)
    end_date = datetime(2024, 1, 31)  # the day must be >= 20
    initial_balance = 5000000

    backtesting = Backtesting(start_date, end_date, initial_balance)
    backtesting.run()
    backtesting.save_results()
