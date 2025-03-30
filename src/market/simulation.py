from src.settings import logger, DATA_PATH, TRADING_FEE
from src.market.portfolio import Portfolio
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd


class MarketSimulation:
    """
    A class to simulate market data for a given date range.
    """

    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        """Initialize the market simulation with a date range."""
        self.start_date = start_date
        self.end_date = end_date
        self.market_data = self.load_market_data()
        self.current_date = start_date
        # Initialize with the first day's data
        self.current_data = self.get_current_stock_data()

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
        """Advance the simulation by one day and update current data."""
        if self.current_date < self.end_date:
            self.current_date += pd.Timedelta(days=1)
            logger.info(f"Advanced to {self.current_date}")
            new_data = self.market_data[self.market_data['datetime']
                                        == self.current_date]
            if new_data.empty:
                logger.debug(
                    f"No market data available for {self.current_date}. Using previous data.")
            else:
                self.current_data = new_data.reset_index(drop=True)
            return True
        else:
            logger.info("Simulation has reached the end date.")
            return False

    def get_current_stock_data(self) -> pd.DataFrame:
        """Get the market data for the current date."""
        return self.market_data[self.market_data['datetime'] == self.current_date].reset_index(drop=True)

    def get_current_financial_data(self) -> pd.DataFrame:
        """Placeholder for fetching financial data."""
        pass

    def get_current_institutional_data(self) -> pd.DataFrame:
        """Placeholder for fetching institutional data."""
        pass

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
        logger.info(f"Buying {quantity} shares of {symbol} at {price} each.")
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_cost': total_cost,
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
        logger.info(f"Selling {quantity} shares of {symbol} at {price} each.")
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_revenue': total_revenue,
            'date': self.current_date
        }

    def get_portfolio_statistics(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        Get the current total value, unrealized
        profit/loss, and realized profit/loss of the portfolio.
        """
        total_value = 0.0
        for asset, quantity in portfolio.assets.items():
            if self.current_data.empty:
                logger.warning(
                    "No market data available for the current date. Using previous data.")
                continue
            try:
                price = self.current_data[self.current_data['tickersymbol']
                                          == asset]['price'].values[0]
            except IndexError:
                logger.warning(
                    f"Asset {asset} not found in current market data.")
                continue
            total_value += price * quantity

        total_value += portfolio.balance
        return {
            'total_value': total_value,
            'unrealized_profit_loss': total_value - portfolio.balance,
            'realized_profit_loss': portfolio.balance - portfolio.initial_balance
        }
