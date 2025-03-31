from src.settings import logger, DATA_PATH, TRADING_FEE
from src.market.portfolio import Portfolio
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np


class MarketSimulation:
    """
    A class to simulate market data for a given date range.
    """

    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        """Initialize the market simulation with a date range."""
        self.start_date = start_date
        self.end_date = end_date
        self.market_data = self.load_market_data()

        # Filter trading days between start_date and end_date
        self.trading_days = self.market_data[
            (self.market_data['datetime'] >= self.start_date) &
            (self.market_data['datetime'] <= self.end_date)
        ]['datetime'].unique()
        # Use np.sort() to sort the DatetimeArray
        self.trading_days = np.sort(self.trading_days)
        # Convert to datetime.date for easier comparison
        self.trading_days = [pd.to_datetime(
            date) for date in self.trading_days]

        if len(self.trading_days) == 0:
            raise ValueError(
                "No trading days available in the specified date range.")

        logger.debug(f"Trading days: {self.trading_days}")
        self.current_trading_day_index = 0
        self.current_date = self.trading_days[self.current_trading_day_index]
        self.current_data = self.get_current_stock_data()

    def is_trading_day(self) -> bool:
        """Check if the current date is a trading day."""
        return self.current_date in self.trading_days

    def load_market_data(self) -> pd.DataFrame:
        """Load market data from a CSV file."""
        file_path = f"{DATA_PATH}/daily_data.csv"
        try:
            logger.info(f"Loading market data from {file_path}")
            df = pd.read_csv(file_path, parse_dates=['datetime'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            logger.info("Market data loaded successfully.")
            return df
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            raise

    def step(self) -> bool:
        """Advance the simulation to the next trading day and update current data."""
        if self.current_trading_day_index + 1 < len(self.trading_days):
            self.current_trading_day_index += 1
            self.current_date = self.trading_days[self.current_trading_day_index]
            # logger.info(
            # f"Advanced to {self.current_date.strftime('%Y-%m-%d')}")
            self.current_data = self.get_current_stock_data()
            return True
        else:
            logger.info("Simulation has reached the end date.")
            return False

    def get_current_stock_data(self) -> pd.DataFrame:
        """Get the market data for the current date."""
        return self.market_data[self.market_data['datetime'] == self.current_date].reset_index(drop=True)

    def buy_stock(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """Simulate buying a stock."""
        if self.current_data.empty:
            logger.debug("No market data available for the current date.")
            return {}
        if symbol not in self.current_data['tickersymbol'].values:
            logger.debug(f"Stock {symbol} not found in current market data.")
            return {}
        price = self.current_data[self.current_data['tickersymbol']
                                  == symbol]['price'].values[0]
        total_cost = price * quantity * (1 + TRADING_FEE)
        logger.debug(f"Buying {quantity} shares of {symbol} at {price} each.")
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
        price = self.current_data[self.current_data['tickersymbol']
                                  == symbol]['price'].values[0]
        total_revenue = price * quantity * (1 - TRADING_FEE)
        logger.debug(f"Selling {quantity} shares of {symbol} at {price} each.")
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_revenue': total_revenue,
            'price': price,
            'date': self.current_date
        }

    def get_portfolio_statistics(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        Get the current total value, unrealized profit/loss, and realized profit/loss of the portfolio.
        """
        total_value = 0.0
        unrealized_profit_loss = 0.0

        for asset, asset_data in portfolio.assets.items():
            quantity = asset_data['quantity']
            average_price = asset_data['average_price']

            if self.current_data.empty:
                logger.warning(
                    "No market data available for the current date.")
                continue
            try:
                price = self.current_data[self.current_data['tickersymbol']
                                          == asset]['price'].values[0]
            except IndexError:
                logger.debug(
                    f"Asset {asset} not found in current market data.")
                # get nearest price
                asset_df = self.market_data[
                    (self.market_data['tickersymbol'] == asset)
                    & (self.market_data['datetime'] <= self.current_date)] \
                    .sort_values('datetime', ascending=False)
                if asset_df.empty:
                    logger.error(
                        f"Asset {asset} not found in market data before {self.current_date}.")
                    continue
                # get the last price before current date
                price = asset_df.iloc[0]['price']
                logger.warning(
                    f"Using last available price for {asset} at {asset_df.iloc[0]['datetime']}: {price}")

            # Calculate the current value of the asset
            current_value = price * quantity
            total_value += current_value

            # Calculate unrealized profit/loss considering the trading fee
            effective_price = price * (1 - TRADING_FEE)
            unrealized_profit_loss += (effective_price -
                                       average_price) * quantity

        # Add the portfolio's cash balance to the total value
        total_value += portfolio.balance

        return {
            'total_value': total_value,
            'unrealized_profit_loss': unrealized_profit_loss,
            'realized_profit_loss': portfolio.realized_profit_loss
        }

    def get_last_day_stock_price(self, symbol: str) -> float:
        """
        Get the last stock price for a given symbol before the current date.
        """
        if self.current_data.empty:
            logger.debug("No market data available for the current date.")
            return 0.0
        if symbol not in self.current_data['tickersymbol'].values:
            logger.debug(f"Stock {symbol} not found in current market data.")
            return 0.0
        last_date = self.current_date - pd.Timedelta(days=1)
        # Filter the market data for the symbol and the last date
        last_price_data = self.market_data[
            (self.market_data['tickersymbol'] == symbol) &
            (self.market_data['datetime'] <= last_date)
        ].sort_values(by='datetime', ascending=False)
        if last_price_data.empty:
            logger.debug(
                f"No price data available for {symbol} before {last_date}.")
            return 0.0
        # Get the last price before the current date
        last_price = last_price_data.iloc[0]['price']
        logger.debug(
            f"Last price for {symbol} before {last_date}: {last_price}")
        return last_price
