from src.settings import logger, DATA_PATH, config
from src.market.portfolio import Portfolio
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np


class MarketSimulation:
    """
    A class to simulate market data for a given date range.
    """

    @staticmethod
    def load_market_data() -> pd.DataFrame:
        """Load market data from a CSV file."""
        file_path = f"{DATA_PATH}/daily_data.csv"
        try:
            logger.debug(f"Loading market data from {file_path}")
            df = pd.read_csv(file_path, parse_dates=['datetime'])
            logger.info("Market data loaded successfully.")
            return df
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            raise

    MARKET_DATA = load_market_data()
    MARKET_DATA_BY_DATE = {
        date: group for date, group in MARKET_DATA.groupby("datetime")
    }
    TRADING_FEE = config["trading_fee"]

    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        """Initialize the market simulation with a date range."""
        self.start_date = start_date
        self.end_date = end_date

        # Precompute trading days and filter market data for the date range
        self.trading_days = self._get_trading_days()
        if not self.trading_days:
            raise ValueError(
                "No trading days available in the specified date range."
            )

        # Cache for the latest price of each stock
        self.latest_price_cache = {}

        logger.debug(f"Trading days: {self.trading_days}")
        self.current_trading_day_index = 0
        self.current_date = self.trading_days[self.current_trading_day_index]
        self.current_data = MarketSimulation.MARKET_DATA_BY_DATE.get(
            self.current_date, pd.DataFrame()
        )

    def _get_trading_days(self) -> List[datetime]:
        """Retrieve and sort trading days within the specified date range."""
        trading_days = MarketSimulation.MARKET_DATA[
            (MarketSimulation.MARKET_DATA["datetime"] >= self.start_date)
            & (MarketSimulation.MARKET_DATA["datetime"] <= self.end_date)
        ]["datetime"].drop_duplicates().sort_values()
        return trading_days.tolist()

    def step(self) -> bool:
        """
        Advance the simulation to the next trading day and update current data.
        """
        if self.current_trading_day_index + 1 < len(self.trading_days):
            self.current_trading_day_index += 1
            self.current_date = self.trading_days[self.current_trading_day_index]
            # Directly retrieve the new market data
            new_data = MarketSimulation.MARKET_DATA_BY_DATE.get(
                self.current_date)
            if new_data is not None:  # Avoid creating empty DataFrames
                self.current_data = new_data

                # Update the latest price cache using NumPy for performance
                tickers = new_data["tickersymbol"].values
                prices = new_data["price"].values
                self.latest_price_cache.update(zip(tickers, prices))
                # logger.debug(f"Advanced to next trading day: {self.current_date}")
            return True
        else:
            logger.info("Simulation has reached the end date.")
            return False

    def get_current_stock_data(self) -> pd.DataFrame:
        """
        Get the market data for the current date.
        This method now simply returns the cached `current_data`.
        """
        return self.current_data

    def buy_stock(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """Simulate buying a stock."""
        if self.current_data.empty:
            logger.debug("No market data available for the current date.")
            return {}
        if symbol not in self.current_data['tickersymbol'].values:
            logger.debug(f"Stock {symbol} not found in current market data.")
            return {}
        price = self.latest_price_cache.get(symbol, 0.0)
        total_cost = price * quantity * (1 + self.TRADING_FEE)
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_cost': total_cost,
            'price': price,
            'date': self.current_date
        }

    def sell_stock(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """Simulate selling a stock."""
        if self.current_data.empty:
            logger.debug("No market data available for the current date.")
            return {}
        if symbol not in self.current_data['tickersymbol'].values:
            logger.debug(f"Stock {symbol} not found in current market data.")
            return {}
        price = self.latest_price_cache.get(symbol, 0.0)
        total_revenue = price * quantity * (1 - self.TRADING_FEE)
        # logger.debug(f"Selling {quantity} shares of {symbol} at {price} each.")
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_revenue': total_revenue,
            'price': price,
            'date': self.current_date
        }

    def get_last_available_price(self, asset: str) -> float:
        """
        Get the last available price for a given asset before the current date.
        """
        # Check if the price is already cached
        if asset in self.latest_price_cache:
            return self.latest_price_cache[asset]

        # Retrieve the last available price from the market data
        asset_data = MarketSimulation.MARKET_DATA[
            (MarketSimulation.MARKET_DATA['tickersymbol'] == asset) &
            (MarketSimulation.MARKET_DATA['datetime'] <= self.current_date)
        ].sort_values('datetime', ascending=False)

        if asset_data.empty:
            logger.error(
                f"Asset {asset} not found in market data before {self.current_date}."
            )
            self.latest_price_cache[asset] = 0.0  # Cache the result as 0.0
            return 0.0

        last_price = asset_data.iloc[0]['price']
        self.latest_price_cache[asset] = last_price  # Cache the result
        return last_price

    def get_portfolio_statistics(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        Optimized function to get portfolio value, unrealized P/L, and realized P/L
        using the latest_price_cache directly for maximum performance.
        """
        total_value = portfolio.balance  # Start with cash balance
        unrealized_profit_loss = 0.0

        # Extract portfolio assets, quantities, and avg prices
        assets = list(portfolio.assets.keys())
        quantities = np.array(
            [portfolio.assets[asset]['quantity'] for asset in assets])
        avg_prices = np.array(
            [portfolio.assets[asset]['average_price'] for asset in assets])

        # Retrieve current prices directly from latest_price_cache
        try:
            current_prices = np.array(
                [self.latest_price_cache[asset] for asset in assets])
        except KeyError as e:
            raise ValueError(f"Missing price data for asset: {e.args[0]}")

        # Compute total portfolio value
        total_value += np.sum(current_prices * quantities)

        # Compute unrealized profit/loss
        effective_prices = current_prices * (1 - self.TRADING_FEE)
        unrealized_profit_loss = np.sum(
            (effective_prices - avg_prices) * quantities)

        return {
            'total_value': total_value,
            'unrealized_profit_loss': unrealized_profit_loss,
            'realized_profit_loss': portfolio.realized_profit_loss
        }

    # def get_portfolio_statistics(self, portfolio: Portfolio) -> Dict[str, Any]:
    #     """
    #     Get the current total value, unrealized profit/loss, and realized profit/loss of the portfolio.
    #     """
    #     total_value = portfolio.balance  # Start with the portfolio's cash balance
    #     unrealized_profit_loss = 0.0

    #     # Precompute a price lookup dictionary for current data
    #     price_lookup = self.current_data.set_index('tickersymbol')[
    #         'price'].to_dict()

    #     for asset, asset_data in portfolio.assets.items():
    #         quantity = asset_data['quantity']
    #         average_price = asset_data['average_price']

    #         # Get the current price or fallback to the last available price
    #         price = price_lookup.get(
    #             asset, self.get_last_available_price(asset))
    #         if price == 0.0:
    #             continue

    #         # Calculate the current value of the asset
    #         current_value = price * quantity
    #         total_value += current_value

    #         # Calculate unrealized profit/loss considering the trading fee
    #         effective_price = price * (1 - self.TRADING_FEE)
    #         unrealized_profit_loss += (effective_price -
    #                                    average_price) * quantity

    #     return {
    #         'total_value': total_value,
    #         'unrealized_profit_loss': unrealized_profit_loss,
    #         'realized_profit_loss': portfolio.realized_profit_loss
    #     }

    def is_last_trading_day(self) -> bool:
        """
        Check if the current date is the last trading day in the simulation.
        """
        return self.current_trading_day_index == len(self.trading_days) - 1
