from src.recommendation.funds import InstitutionalScoring
from src.recommendation.stocks import FinancialScoring
from src.settings import logger
from typing import List, Tuple
import pandas as pd


class StocksRanking:
    """
    Rank stocks at given month and year based on institutional and 
    financial scores.
    """

    def __init__(self, month: int, year: int, symbols: List[str]):
        # get the last month and year, and last quarter
        self.month = month - 1 if month > 1 else 12
        self.year = year - 1 if month == 1 else year
        self.quarter = (month - 1) // 3 if month > 3 else 4
        self.quarter_year = year - 1 if self.quarter == 4 else year
        self.symbols = symbols

    def get_all_scores(self) -> pd.DataFrame:
        """
        Retrieve and merge institutional and financial scores for all symbols.
        If any scores are missing, set them to 0.
        """
        inst_scoring = InstitutionalScoring(
            self.month, self.year, self.symbols).get_scores()
        fin_scoring = FinancialScoring(
            self.quarter, self.quarter_year, self.symbols).get_scores()

        # Merge on symbol with an outer join to include all symbols
        df = pd.merge(inst_scoring, fin_scoring, on="symbol", how="outer")

        logger.debug(
            f"Scores DataFrame after merge: \n{df.head(10).to_string(index=False)}")

        return df

    def calculate_institutional_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the institutional score based on fund net buying, number of fund holdings, and net fund change.
        """
        # Normalize fund_net_buying, number_fund_holdings, and net_fund_change
        for column in ["fund_net_buying", "number_fund_holdings", "net_fund_change"]:
            df[column] = (df[column] - df[column].min()) / \
                (df[column].max() - df[column].min())

        # Calculate institutional score
        df["inst_score"] = (
            0.45 * df["fund_net_buying"] +
            0.35 * df["number_fund_holdings"] +
            0.2 * df["net_fund_change"]
        )

        # If any score component is NaN, set inst_score to 0
        df.loc[df[["fund_net_buying", "number_fund_holdings",
                   "net_fund_change"]].isnull().any(axis=1), "inst_score"] = 0
        df["inst_score"] = df["inst_score"].fillna(0)
        df["inst_score"] = df["inst_score"].clip(lower=0)

    def calculate_fin_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the financial score (fin_score) based on ROE, PE, revenue growth, and cash ratio.
        If any financial score component is NaN, set the fin_score to 0.
        """
        # Clip debt_to_equity for normalization
        df["debt_to_equity"] = df["debt_to_equity"].clip(
            lower=0.0, upper=2.0)  # Cap at 2.0 for normalization

        # Normalize cash ratio: less deviation from the mean is better
        df["cash_ratio_normalized"] = df["cash_ratio"].apply(
            lambda x: 1 - abs(x - df["cash_ratio"].mean()
                              ) / df["cash_ratio"].std()
        )
        df["cash_ratio_normalized"] = df["cash_ratio_normalized"].clip(
            lower=0.0, upper=1.0)
        # P/E ratio score: (revenue_growth - pe) / revenue_growth
        df["pe_score"] = (df["revenue_growth"] - df["pe"]) / \
            df["revenue_growth"]
        df["pe_score"] = df["pe_score"].clip(lower=0.0)
        # Normalize ROE, revenue growth, and debt_to_equity (larger is better)
        for column in ["roe", "revenue_growth", "debt_to_equity", "pe_score"]:
            if df[column].max() != df[column].min():  # Avoid division by zero
                df[f"{column}_normalized"] = (
                    df[column] - df[column].min()) / (df[column].max() - df[column].min())
            else:
                # If all values are the same, set normalized value to 0
                df[f"{column}_normalized"] = 0

        # Check for NaN values in financial score components
        financial_columns = [
            "roe_normalized",
            "revenue_growth_normalized",
            "debt_to_equity_normalized",
            "cash_ratio_normalized",
            "pe_score_normalized",
        ]
        df["fin_score"] = (
            0.30 * df["roe_normalized"] +
            0.15 * df["revenue_growth_normalized"] +
            0.10 * df["debt_to_equity_normalized"] +
            0.10 * df["cash_ratio_normalized"] +
            0.35 * df["pe_score_normalized"]
        )

        # If any financial component is NaN, set fin_score to 0
        df.loc[df[financial_columns].isnull().any(axis=1), "fin_score"] = 0

        # If fin_score is NaN, set it to 0
        df["fin_score"] = df["fin_score"].fillna(0)
        df["fin_score"] = df["fin_score"].clip(lower=0)

    def get_ranking(self) -> List[Tuple[str, float]]:
        df = self.get_all_scores()

        # Calculate institutional score
        self.calculate_institutional_score(df)

        # Calculate financial score
        self.calculate_fin_score(df)

        # Combine institutional and financial scores into a total score
        df["score"] = 0.6 * df["inst_score"] + 0.4 * df["fin_score"]

        # Sort by score and return the symbols
        df = df.sort_values(by=["score"], ascending=False)
        df = df.reset_index(drop=True)

        logger.debug(f"Institutional and financial scores:\n"
                     f"{df[['symbol', 'inst_score', 'fin_score', 'score']].head(10).to_string(index=False)}")
        # Return the top 3 symbols with their scores
        ranking = df[["symbol", "score"]].values.tolist()
        return ranking

    def recommend(self) -> List[str]:
        ranking = self.get_ranking()[:3]
        return [symbol for symbol, _ in ranking]
