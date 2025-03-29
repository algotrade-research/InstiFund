from src.settings import logger, DATA_PATH, TRADING_FEE
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

    def step(self) -> None:
        """Advance the simulation by one day."""
        if self.current_date < self.end_date:
            self.current_date += pd.Timedelta(days=1)
            logger.info(f"Advanced to {self.current_date}")
        else:
            logger.info("Simulation has reached the end date.")

    def get_current_stock_data(self) -> pd.DataFrame:
        """Get the market data for the current date."""
        current_data = self.market_data[self.market_data['datetime']
                                        == self.current_date]
        if current_data.empty:
            logger.warning(f"No market data available for {self.current_date}")
        return current_data.reset_index(drop=True)

    def get_current_financial_data(self) -> pd.DataFrame:
        pass

    def get_current_institutional_data(self) -> pd.DataFrame:
        pass

    def buy_stock(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """Simulate buying a stock."""
        current_data = self.get_current_stock_data()
        if current_data.empty:
            logger.warning("No market data available for the current date.")
            return {}
        price = current_data[current_data['symbol']
                             == symbol]['close'].values[0]
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
        current_data = self.get_current_stock_data()
        if current_data.empty:
            logger.warning("No market data available for the current date.")
            return {}
        price = current_data[current_data['symbol']
                             == symbol]['close'].values[0]
        total_revenue = price * quantity * (1 - TRADING_FEE)
        logger.info(f"Selling {quantity} shares of {symbol} at {price} each.")
        return {
            'symbol': symbol,
            'quantity': quantity,
            'total_revenue': total_revenue,
            'date': self.current_date
        }

    def get_portfolio_value(self, portfolio: List[Dict[str, Any]]) -> float:
        """Calculate the total value of the portfolio."""
        total_value = 0.0
        for stock in portfolio:
            symbol = stock['symbol']
            quantity = stock['quantity']
            current_data = self.get_current_stock_data()
            price = current_data[current_data['symbol']
                                 == symbol]['close'].values[0]
            total_value += price * quantity
        logger.info(f"Total portfolio value: {total_value}")
        return total_value
