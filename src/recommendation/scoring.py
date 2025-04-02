from src.recommendation.funds import InstitutionalScoring
from src.recommendation.stocks import FinancialScoring
from src.settings import logger, DATA_PATH
from typing import List, Tuple, Dict, Any
import pandas as pd
import os


try:
    MONTHLY_SCORES_DF = pd.read_csv(
        os.path.join(DATA_PATH, "monthly_scores.csv"))
    logger.info(
        f"Monthly scores data loaded successfully with {len(MONTHLY_SCORES_DF)} rows."
    )
except Exception as e:
    logger.error(f"Failed to load monthly scores data: {e}")


class StocksRanking:
    """
    Rank stocks at a given month and year based on institutional and financial scores.
    """

    def __init__(self, month: int, year: int, symbols: List[str],
                 params: Dict[str, Any]) -> None:
        # Calculate the last month, year, and quarter
        self.month = month
        self.year = year
        self.symbols = symbols
        self.params = params

    def get_all_scores(self) -> pd.DataFrame:
        """
        Retrieve and merge institutional and financial scores for all symbols.
        If any scores are missing, set them to 0.
        """
        df = MONTHLY_SCORES_DF[
            (MONTHLY_SCORES_DF["month"] == self.month) &
            (MONTHLY_SCORES_DF["year"] == self.year) &
            (MONTHLY_SCORES_DF["symbol"].isin(self.symbols))
        ].reset_index(drop=True)
        return df

    def calculate_institutional_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the institutional score based on fund net buying, number of fund holdings, and net fund change.
        """
        # Normalize columns
        for column in ["fund_net_buying", "number_fund_holdings", "net_fund_change"]:
            col_min, col_max = df[column].min(), df[column].max()
            if col_max != col_min:  # Avoid division by zero
                df[column] = (df[column] - col_min) / (col_max - col_min)
            else:
                df[column] = 0

        # Calculate institutional score
        net_fund_change_w = 1.0 - self.params["fund_net_buying"]
        - self.params["number_fund_holdings"]
        df["inst_score"] = (
            self.params["fund_net_buying"] * df["fund_net_buying"]
            + self.params["number_fund_holdings"] * df["number_fund_holdings"]
            + net_fund_change_w * df["net_fund_change"]
        ).fillna(0).clip(lower=0)

    def calculate_fin_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the financial score (fin_score) based on ROE, PE, revenue growth, and debt-to-equity ratio.
        """
        # Clip debt_to_equity for normalization
        df["debt_to_equity"] = df["debt_to_equity"].clip(lower=0.0, upper=2.0)

        # Calculate P/E ratio score
        df["pe_score"] = (
            (df["revenue_growth"] - df["pe"]) / df["revenue_growth"]
        ).clip(lower=0.0)

        # Normalize columns
        for column in ["roe", "revenue_growth", "debt_to_equity", "pe_score"]:
            col_min, col_max = df[column].min(), df[column].max()
            if col_max != col_min:  # Avoid division by zero
                df[f"{column}_normalized"] = (
                    df[column] - col_min) / (col_max - col_min)
            else:
                df[f"{column}_normalized"] = 0

        # Calculate financial score
        de_weight = 1.0 - self.params["roe"] - \
            self.params["revenue_growth"] - self.params["pe"]
        df["fin_score"] = (
            self.params["roe"] * df["roe_normalized"]
            + self.params["revenue_growth"] * df["revenue_growth_normalized"]
            + de_weight * df["debt_to_equity_normalized"]
            + self.params["pe"] * df["pe_score_normalized"]
        ).fillna(0).clip(lower=0)

    def get_ranking(self) -> List[Tuple[str, float]]:
        """
        Combine institutional and financial scores into a total score and rank the stocks.
        :return: List of tuples containing stock symbols and their scores.
        """
        df = self.get_all_scores()

        # Calculate institutional and financial scores
        self.calculate_institutional_score(df)
        self.calculate_fin_score(df)

        # Combine scores into a total score
        df["score"] = self.params["institutional_weight"] * df["inst_score"] \
            + (1.0 - self.params["institutional_weight"]) * df["fin_score"]

        # Sort by score in descending order
        df = df.sort_values(by="score", ascending=False).reset_index(drop=True)

        logger.debug(
            f"Institutional and financial scores:\n"
            f"{df[['symbol', 'inst_score', 'fin_score', 'score']]
               .head(10).to_string(index=False)}"
        )

        # Return the top-ranked symbols with their scores
        return df[["symbol", "score"]].values.tolist()
