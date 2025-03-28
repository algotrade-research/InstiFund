from src.recommendation.data import FUND_DF
import os
import pandas as pd
from src.utitlies import get_last_month
from typing import Tuple
import logging
import logging.config

# Load logging configuration
logging.config.fileConfig(os.path.join(
    os.path.dirname(__file__), "../../config/logging.conf"))
logger = logging.getLogger("my_logger")


class InstitutionalScoring:

    class FinancialStatement:
        def __init__(self, month: int, year: int, symbol: str):
            self.month = month
            self.year = year
            self.symbol = symbol
            logger.debug(
                f"Initializing FinancialStatement for {symbol} ({month}/{year})")
            self.data = self.get_data()

        def get_data(self) -> pd.DataFrame:
            """
            Load the financial statement data
            of the stock with the given date:
            - Fund Code
            - Market Price
            - Quantity
            - Value
            - Total Asset Ratio
            """
            logger.debug(
                f"Fetching data for {self.symbol} ({self.month}/{self.year})")
            df = FUND_DF[FUND_DF["Category"] == self.symbol]
            df = df[df["Date"].dt.month == self.month]
            df = df[df["Date"].dt.year == self.year]
            if df.empty:
                logger.warning(
                    f"No data found for {self.symbol} ({self.month}/{self.year})")
            else:
                logger.info(
                    f"Data fetched for {self.symbol} ({self.month}/{self.year}): {len(df)} rows")
            # sort by Fund Code
            df = df.sort_values(by=["Fund Code"])
            df = df.reset_index(drop=True)
            return df

    def __init__(self, month: int, year: int, symbol: str):
        self.month = month
        self.year = year
        self.symbol = symbol
        logger.debug(
            f"Initializing InstitutionalScoring for {symbol} ({month}/{year})")

    def get_scores(self) -> Tuple[float, int, int]:
        logger.info(
            f"Calculating scores for {self.symbol} ({self.month}/{self.year})")
        current = self.FinancialStatement(self.month, self.year, self.symbol)
        last_month, last_year = get_last_month(self.month, self.year)
        last = self.FinancialStatement(last_month, last_year, self.symbol)

        try:
            fund_net_buying = (current.data["Value"].sum()
                               - last.data["Value"].sum()) / last.data["Value"].sum()
        except ZeroDivisionError:
            logger.error(
                f"Division by zero encountered for {self.symbol} ({self.month}/{self.year})")
            fund_net_buying = 0.0

        number_fund_holdings = len(current.data)

        # number funds increase their net asset value - number funds decrease
        # their net asset value
        net_fund_change = 0
        for i in range(len(current.data)):
            if current.data["Value"].iloc[i] > last.data["Value"].iloc[i]:
                net_fund_change += 1
            elif current.data["Value"].iloc[i] < last.data["Value"].iloc[i]:
                net_fund_change -= 1

        logger.info(f"Scores for {self.symbol} ({self.month}/{self.year}): "
                    f"fund_net_buying={fund_net_buying}, "
                    f"number_fund_holdings={number_fund_holdings}, "
                    f"net_fund_change={net_fund_change}")

        return fund_net_buying, number_fund_holdings, net_fund_change
