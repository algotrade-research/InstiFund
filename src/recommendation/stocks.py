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
        # logger.info(
        #     f"Head the dataframe: \n{self.data.head(10).to_string(index=False)}"
        # )
        last_quarter = self.quarter - 1 if self.quarter > 1 else 4
        last_year = self.year - 1 if last_quarter == 4 else self.year
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
            roe = df["ROE"].values[0]
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
            debt_to_equity = df["Debt/Equity"].values[0]
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
            current_revenue = cur_df["Revenue"].values[0]
            last_revenue = last_df["Revenue"].values[0]
            revenue_growth = (
                (current_revenue - last_revenue) / last_revenue) * 100
            return revenue_growth
        except Exception as e:
            logger.error(
                f"Error calculating Revenue Growth for {cur_df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_cash_ratio(self, df: pd.DataFrame) -> float:
        """
        Calculate the cash ratio for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: Cash ratio value.
        """
        try:
            cash_and_cash_equivalents = df["Cash"].values[0]
            liabilities = df["Liabilities"].values[0]
            cash_ratio = cash_and_cash_equivalents / liabilities
            return cash_ratio
        except Exception as e:
            logger.error(
                f"Error calculating Cash Ratio for {df['tickersymbol'].iloc[0]}: {e}")
            return 0.0

    def get_pe(self, df: pd.DataFrame) -> float:
        """
        Calculate the Price to Earnings (P/E) ratio for the given DataFrame.
        :param df: DataFrame containing financial data for a specific symbol.
        :return: P/E ratio value.
        """
        try:
            pe = df["P/E"].values[0]
            return pe
        except Exception as e:
            logger.error(
                f"Error calculating P/E Ratio for {df['tickersymbol'].iloc[0]}"
                f" at Q{self.quarter}/{self.year}"
                f": {e}")
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
                # vnstock_data = self.load_vnstock_financial_data(symbol)
                # if vnstock_data.empty:
                logger.debug(
                    f"No data available for {symbol} (Q{self.quarter}/{self.year}). Skipping.")
                # continue
                # scores.append({
                #     "symbol": symbol,
                #     "roe": vnstock_data["roe"],
                #     "debt_to_equity": vnstock_data["debt_to_equity"],
                #     "revenue_growth": vnstock_data["revenue_growth"],
                #     "current_ratio": vnstock_data["current_ratio"]
                # })
            else:
                roe = self.get_roe(df)
                debt_to_equity = self.get_debt_to_equity(df)
                revenue_growth = self.get_revenue_growth(df, last_df)
                cash_ratio = self.get_cash_ratio(df)
                pe = self.get_pe(df)
                scores.append({
                    "symbol": symbol,
                    "roe": roe,
                    "debt_to_equity": debt_to_equity,
                    "revenue_growth": revenue_growth,
                    "cash_ratio": cash_ratio,
                    "pe": pe
                })
        # Convert the list of scores to a DataFrame
        scores = pd.DataFrame(scores)
        logger.debug(
            f"Scores DataFrame before normalization: \n{scores.head(10).to_string(index=False)}")
        return scores
