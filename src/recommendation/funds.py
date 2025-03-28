from src.recommendation.data import FUND_DF
import os
import pandas as pd
from src.utitlies import get_last_month
from typing import Tuple


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
            # sort by Fund Code
            df = df.sort_values(by=["Fund Code"])
            df = df.reset_index(drop=True)
            return df

    def __init__(self, month: int, year: int, symbol: str):
        self.month = month
        self.year = year
        self.symbol = symbol

    def get_scores(self) -> Tuple[float, int, int]:
        current = self.FinancialStatement(self.month, self.year, self.symbol)
        last_month, last_year = get_last_month(self.month, self.year)
        last = self.FinancialStatement(last_month, last_year, self.symbol)

        fund_net_buying = (current.data["Value"].sum()
                           - last.data["Value"].sum()) / last.data["Value"].sum()

        number_fund_holdings = len(current.data)

        # number funds increase their net asset value - number funds decrease
        # their net asset value
        net_fund_change = 0
        for i in range(len(current.data)):
            if current.data["Value"].iloc[i] > last.data["Value"].iloc[i]:
                net_fund_change += 1
            elif current.data["Value"].iloc[i] < last.data["Value"].iloc[i]:
                net_fund_change -= 1

        return fund_net_buying, number_fund_holdings, net_fund_change
