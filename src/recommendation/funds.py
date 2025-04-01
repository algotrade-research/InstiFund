from src.recommendation.data import FUND_DF
import os
import pandas as pd
from src.utitlies import get_last_month
from src.settings import logger
from typing import Tuple, List


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

        # Pre-filter the FUND_DF once for the current and last periods to avoid redundant filtering
        current_period_df = FUND_DF[
            (FUND_DF["Date"].dt.month == self.month) & (
                FUND_DF["Date"].dt.year == self.year)
        ]
        last_month, last_year = get_last_month(self.month, self.year)
        last_period_df = FUND_DF[
            (FUND_DF["Date"].dt.month == last_month) & (
                FUND_DF["Date"].dt.year == last_year)
        ]

        # Group data by symbol for faster access
        current_grouped = current_period_df.groupby("Category")
        last_grouped = last_period_df.groupby("Category")

        for symbol in self.symbols:
            current_data = current_grouped.get_group(
                symbol) if symbol in current_grouped.groups else pd.DataFrame()
            last_data = last_grouped.get_group(
                symbol) if symbol in last_grouped.groups else pd.DataFrame()

            if current_data.empty or last_data.empty:
                scores.append({
                    "symbol": symbol,
                    "fund_net_buying": 0.0,
                    "number_fund_holdings": 0,
                    "net_fund_change": 0
                })
                continue

            try:
                fund_net_buying = (current_data["Value"].sum(
                ) - last_data["Value"].sum()) / last_data["Value"].sum()
            except ZeroDivisionError:
                logger.error(
                    f"Division by zero encountered for {symbol} ({self.month}/{self.year})")
                fund_net_buying = 0.0

            number_fund_holdings = len(current_data)

            # Calculate net fund change
            merged_df = pd.merge(
                current_data, last_data, on="Fund Code", how="outer", suffixes=("_current", "_last")
            ).fillna(0)
            net_fund_change = (
                (merged_df["Value_current"] > merged_df["Value_last"]).sum() -
                (merged_df["Value_current"] < merged_df["Value_last"]).sum()
            )

            scores.append({
                "symbol": symbol,
                "fund_net_buying": fund_net_buying,
                "number_fund_holdings": number_fund_holdings,
                "net_fund_change": net_fund_change
            })

        return pd.DataFrame(scores)
