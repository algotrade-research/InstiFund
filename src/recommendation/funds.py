from src.recommendation.data import FUND_DF
import os
import pandas as pd
from src.utitlies import get_last_month
from typing import Tuple, List
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
            df = FUND_DF[FUND_DF["Category"] == self.symbol]
            df = df[df["Date"].dt.month == self.month]
            df = df[df["Date"].dt.year == self.year]
            df = df.sort_values(by=["Fund Code"])
            df = df.reset_index(drop=True)
            return df

    def __init__(self, month: int, year: int, symbols: List[str]):
        self.month = month
        self.year = year
        self.symbols = symbols

    def get_scores(self) -> pd.DataFrame:
        """
        Calculate scores for a list of symbols and return a DataFrame.
        :return: pd.DataFrame with columns ['Symbol', 'Fund Net Buying', 'Number Fund Holdings', 'Net Fund Change']
        """
        scores = []

        for symbol in self.symbols:
            # # logger.debug(
            #     f"Calculating scores for {symbol} ({self.month}/{self.year})")
            current = self.FinancialStatement(self.month, self.year, symbol)
            last_month, last_year = get_last_month(self.month, self.year)
            last = self.FinancialStatement(last_month, last_year, symbol)

            if current.data.empty or last.data.empty:
                # logger.debug(
                # f"No data available for {symbol} ({self.month}/{self.year}). Skipping.")
                scores.append({
                    "symbol": symbol,
                    "fund_net_buying": 0.0,
                    "number_fund_holdings": 0,
                    "net_fund_change": 0
                })
                continue

            try:
                fund_net_buying = (current.data["Value"].sum(
                ) - last.data["Value"].sum()) / last.data["Value"].sum()
            except ZeroDivisionError:
                logger.error(
                    f"Division by zero encountered for {symbol} ({self.month}/{self.year})")
                fund_net_buying = 0.0

            number_fund_holdings = len(current.data)

            # Calculate net fund change
            net_fund_change = 0
            merged_df = pd.merge(current.data, last.data, on="Fund Code",
                                 how="outer", suffixes=("_current", "_last"))
            merged_df = merged_df.fillna(0)
            net_fund_change += len(
                merged_df[merged_df["Value_current"] > merged_df["Value_last"]])
            net_fund_change -= len(
                merged_df[merged_df["Value_current"] < merged_df["Value_last"]])

            # logger.debug(f"Scores for {symbol} ({self.month}/{self.year}): "
            #              f"fund_net_buying={fund_net_buying}, "
            #              f"number_fund_holdings={number_fund_holdings}, "
            #              f"net_fund_change={net_fund_change}")

            scores.append({
                "symbol": symbol,
                "fund_net_buying": fund_net_buying,
                "number_fund_holdings": number_fund_holdings,
                "net_fund_change": net_fund_change
            })

        return pd.DataFrame(scores)
