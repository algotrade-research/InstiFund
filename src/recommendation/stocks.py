from src.recommendation.data import FINANCIAL_DF
from src.utitlies import get_last_month
from src.settings import logger
import pandas as pd
from datetime import datetime
from typing import List

# USED_COLUMNS = [
#     "Revenue (Bn. VND)",
#     "P/E"
#     "ROE (%)",
#     "Debt/Equity",
#     "Cash and cash equivalents (Bn. VND)",
#     "LIABILITIES (Bn. VND)",
# ]


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

    # def get_roe(self, df: pd.DataFrame) -> float:
    #     """
    #     Calculate the Return on Equity (ROE) for the given DataFrame.
    #     :param df: DataFrame containing financial data for a specific symbol.
    #     :return: ROE value.
    #     """
    #     try:
    #         # if ROE exist in "name" column then return it
    #         net_income = df[df["name"] ==
    #                         "Net Profit After Tax Attribute"
    #                         " to Majority Shareholders"]["value"].values[0]
    #         equity = df[df["name"] == "Shareholders Equity"]["value"].values[0]
    #         net_income = float(net_income)
    #         equity = float(equity)
    #         roe = (net_income / equity) * 100
    #         roe = round(roe, 2)
    #         return roe
    #     except Exception as e:
    #         logger.error(
    #             f"Error calculating ROE for {df['tickersymbol'].iloc[0]}: {e}")
    #         return 0.0

    # def get_debt_to_equity(self, df: pd.DataFrame) -> float:
    #     """
    #     Calculate the Debt to Equity ratio for the given DataFrame.
    #     :param df: DataFrame containing financial data for a specific symbol.
    #     :return: Debt to Equity ratio value.
    #     """
    #     try:
    #         total_debt = df[df["name"] == "Liabilities"]["value"].values[0]
    #         equity = df[df["name"] == "Shareholders Equity"]["value"].values[0]
    #         total_debt = float(total_debt)
    #         equity = float(equity)
    #         debt_to_equity = total_debt / equity
    #         return debt_to_equity
    #     except Exception as e:
    #         logger.error(
    #             f"Error calculating Debt to Equity for {df['tickersymbol'].iloc[0]}: {e}")
    #         return 0.0

    # def get_revenue_growth(self, cur_df: pd.DataFrame, last_df: pd.DataFrame) -> float:
    #     """
    #     Calculate the revenue growth for the given DataFrame.
    #     :param df: DataFrame containing financial data for a specific symbol.
    #     :return: Revenue growth value.
    #     """
    #     try:
    #         current_revenue = cur_df[cur_df["name"]
    #                                  == "Gross Revenue"]["value"].values[0]
    #         last_revenue = last_df[last_df["name"]
    #                                == "Gross Revenue"]["value"].values[0]
    #         current_revenue = float(current_revenue)
    #         last_revenue = float(last_revenue)
    #         revenue_growth = (
    #             (current_revenue - last_revenue) / last_revenue) * 100
    #         return revenue_growth
    #     except Exception as e:
    #         logger.error(
    #             f"Error calculating Revenue Growth for {cur_df['tickersymbol'].iloc[0]}: {e}")
    #         return 0.0

    # def get_current_ratio(self, df: pd.DataFrame) -> float:
    #     """
    #     Calculate the current ratio for the given DataFrame.
    #     :param df: DataFrame containing financial data for a specific symbol.
    #     :return: Current ratio value.
    #     """
    #     try:
    #         current_assets = df[df["name"] ==
    #                             "Current Assets"]["value"].values[0]
    #         current_liabilities = df[df["name"] ==
    #                                  "Current Liabilities"]["value"].values[0]
    #         current_assets = float(current_assets)
    #         current_liabilities = float(current_liabilities)
    #         current_ratio = current_assets / current_liabilities
    #         return current_ratio
    #     except Exception as e:
    #         logger.error(
    #             f"Error calculating Current Ratio for {df['tickersymbol'].iloc[0]}: {e}")
    #         return 0.0

    # def load_vnstock_financial_data(self, symbol: str) -> Dict[str, float]:
    #     """
    #     Load financial data from vnstock for the given symbol.
    #     :param symbol: Stock symbol.
    #     :return: DataFrame containing financial data.
    #     """
    #     try:
    #         income_statement = vnstock.finance.income_statement(
    #             period="quarter", symbol=symbol, lang="en")[["Revenue (Bn. VND)", "yearReport", "lengthReport"]]
    #         income_statement.rename(
    #             columns={"Revenue (Bn. VND)": "Revenue", "yearReport": "year", "lengthReport": "quarter"}, inplace=True)
    #         # decrease quarter by 1 to match the quarter in the data
    #         income_statement["quarter"] = income_statement["quarter"].apply(
    #             lambda x: x - 1)
    #         current_revenue = income_statement[(income_statement["year"] == self.year) &
    #                                            (income_statement["quarter"] == self.quarter)]["Revenue (Bn. VND)"].values[0]
    #         last_revenue = income_statement["Revenue (Bn. VND)"].values[0]
    #         return df
    #     except Exception as e:
    #         logger.error(f"Error loading VNStock data for {symbol}: {e}")
    #         return pd.DataFrame()

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
                logger.warning(
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
