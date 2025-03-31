from src.recommendation.data import FINANCIAL_DF
from src.utitlies import get_last_month
from src.settings import logger
import pandas as pd
from datetime import datetime
from typing import List

USED_COLUMNS = [
    "Gross Revenue",
    "Net Profit After Tax Attribute to Majority Shareholders",
    "Shareholders Equity",
    "Current Assets",
    "Current Liabilities",
    "Liabilities",
]


class FinancialScoring:
    def __init__(self, quarter: int, year: int, symbols: List[str]):
        self.quarter = quarter
        self.year = year
        self.symbols = symbols
        self.data = self.get_data(self.quarter, self.year)
        # logger.info(
        #     f"Head the dataframe: \n{self.data.head(10).to_string(index=False)}"
        # )

        last_quarter = self.quarter - 1 if self.quarter > 0 else 3
        last_year = self.year - 1 if self.quarter == 0 else self.year
        self.last_data = self.get_data(last_quarter, last_year)

    def get_data(self, quarter: int, year: int) -> pd.DataFrame:
        """
        Load the financial data for the given month and year.
        """
        df = FINANCIAL_DF[FINANCIAL_DF["tickersymbol"].isin(self.symbols)]
        df = df[(df["quarter"] == quarter) &
                (df["year"] == year)]
        df = df.reset_index(drop=True)
        return df

    def get_roe(self, df: pd.DataFrame) -> float:
        """
        Calculate the Return on Equity (ROE) for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: ROE value.
        """
        try:
            # if ROE exist in "name" column then return it
            net_income = df[df["name"] ==
                            "Net Profit After Tax Attribute"
                            " to Majority Shareholders"]["value"].values[0]
            equity = df[df["name"] == "Shareholders Equity"]["value"].values[0]
            net_income = float(net_income)
            equity = float(equity)
            roe = (net_income / equity) * 100
            roe = round(roe, 2)
            return roe
        except Exception as e:
            logger.error(
                f"Error calculating ROE for {df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_debt_to_equity(self, df: pd.DataFrame) -> float:
        """
        Calculate the Debt to Equity ratio for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: Debt to Equity ratio value.
        """
        try:
            total_debt = df[df["name"] == "Liabilities"]["value"].values[0]
            equity = df[df["name"] == "Shareholders Equity"]["value"].values[0]
            total_debt = float(total_debt)
            equity = float(equity)
            debt_to_equity = total_debt / equity
            return debt_to_equity
        except Exception as e:
            logger.error(
                f"Error calculating Debt to Equity for {df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_revenue_growth(self, cur_df: pd.DataFrame, last_df: pd.DataFrame) -> float:
        """
        Calculate the revenue growth for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: Revenue growth value.
        """
        try:
            current_revenue = cur_df[cur_df["name"]
                                     == "Gross Revenue"]["value"].values[0]
            last_revenue = last_df[last_df["name"]
                                   == "Gross Revenue"]["value"].values[0]
            current_revenue = float(current_revenue)
            last_revenue = float(last_revenue)
            revenue_growth = (
                (current_revenue - last_revenue) / last_revenue) * 100
            return revenue_growth
        except Exception as e:
            logger.error(
                f"Error calculating Revenue Growth for {cur_df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_current_ratio(self, df: pd.DataFrame) -> float:
        """
        Calculate the current ratio for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: Current ratio value.
        """
        try:
            current_assets = df[df["name"] ==
                                "Current Assets"]["value"].values[0]
            current_liabilities = df[df["name"] ==
                                     "Current Liabilities"]["value"].values[0]
            current_assets = float(current_assets)
            current_liabilities = float(current_liabilities)
            current_ratio = current_assets / current_liabilities
            return current_ratio
        except Exception as e:
            logger.error(
                f"Error calculating Current Ratio for {df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_scores(self) -> pd.DataFrame:
        """
        Calculate scores for the financial data.
        :return: pd.DataFrame with columns ['symbol', 'score']
        """
        scores = []

        for symbol in self.symbols:
            df = self.data[self.data["tickersymbol"] == symbol]
            last_df = self.last_data[self.last_data["tickersymbol"] == symbol]
            if df.empty or last_df.empty:
                logger.warning(
                    f"No data available for {symbol} (Q{self.quarter+1}/{self.year}). Skipping.")
                continue

            roe = self.get_roe(df)
            debt_to_equity = self.get_debt_to_equity(df)
            revenue_growth = self.get_revenue_growth(df, last_df)
            current_ratio = self.get_current_ratio(df)
            scores.append({
                "symbol": symbol,
                "roe": roe,
                "debt_to_equity": debt_to_equity,
                "revenue_growth": revenue_growth,
                "current_ratio": current_ratio
            })
            # logger.debug(
            #     f"Scores for {symbol} (Q{self.quarter+1}/{self.year}): "
            #     f"roe={roe}, pe={pe}, revenue_growth={revenue_growth}, "
            #     f"current_ratio={current_ratio}")

        return pd.DataFrame(scores)
