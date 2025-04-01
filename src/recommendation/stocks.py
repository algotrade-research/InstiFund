from src.recommendation.data import FINANCIAL_DF
from src.utitlies import get_last_month
from src.settings import logger
import pandas as pd
from datetime import datetime
from typing import List


class FinancialScoring:
    def __init__(self, quarter: int, year: int, symbols: List[str]):
        self.quarter = quarter
        self.year = year
        self.symbols = symbols
        self.data = self.get_data(self.quarter, self.year)
        last_quarter = self.quarter - 1 if self.quarter > 1 else 4
        last_year = self.year - 1 if last_quarter == 4 else self.year
        self.last_data = self.get_data(last_quarter, last_year)

    def get_data(self, quarter: int, year: int) -> pd.DataFrame:
        """
        Load the financial data for the given quarter and year.
        """
        df = FINANCIAL_DF[
            (FINANCIAL_DF["tickersymbol"].isin(self.symbols)) &
            (FINANCIAL_DF["quarter"] == quarter) &
            (FINANCIAL_DF["year"] == year)
        ].reset_index(drop=True)
        return df

    def safe_get_value(self, df: pd.DataFrame, column: str, default: float = 0.0) -> float:
        """
        Safely retrieve a value from a DataFrame column.
        :param df: DataFrame containing financial data.
        :param column: Column name to retrieve the value from.
        :param default: Default value to return if the column is missing or empty.
        :return: Retrieved value or default.
        """
        if column in df.columns and not df.empty:
            return df[column].iloc[0]
        return default

    def get_revenue_growth(self, cur_df: pd.DataFrame, last_df: pd.DataFrame) -> float:
        """
        Calculate the revenue growth for the given DataFrames.
        :param cur_df: Current quarter's financial data.
        :param last_df: Last quarter's financial data.
        :return: Revenue growth value.
        """
        current_revenue = self.safe_get_value(cur_df, "Revenue")
        last_revenue = self.safe_get_value(last_df, "Revenue")
        if last_revenue > 0:
            return ((current_revenue - last_revenue) / last_revenue) * 100
        return 0.0

    def get_scores(self) -> pd.DataFrame:
        """
        Calculate scores for the financial data.
        :return: pd.DataFrame with columns ['symbol', 'roe', 'debt_to_equity', 'revenue_growth', 'cash_ratio', 'pe']
        """
        scores = []

        for symbol in self.symbols:
            cur_df = self.data[self.data["tickersymbol"] == symbol]
            last_df = self.last_data[self.last_data["tickersymbol"] == symbol]

            if cur_df.empty or last_df.empty:
                logger.debug(
                    f"No data available for {symbol} (Q{self.quarter}/{self.year}). Skipping.")
                continue

            scores.append({
                "symbol": symbol,
                "roe": self.safe_get_value(cur_df, "ROE"),
                "debt_to_equity": self.safe_get_value(cur_df, "Debt/Equity"),
                "revenue_growth": self.get_revenue_growth(cur_df, last_df),
                # "cash_ratio": self.safe_get_value(cur_df, "Cash") / max(self.safe_get_value(cur_df, "Liabilities"), 1),
                "pe": self.safe_get_value(cur_df, "P/E")
            })

        scores_df = pd.DataFrame(scores)
        logger.debug(
            f"Scores DataFrame before normalization: \n{scores_df.head(10).to_string(index=False)}")
        return scores_df
