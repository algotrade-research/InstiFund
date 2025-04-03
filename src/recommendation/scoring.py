from src.settings import logger, DATA_PATH
from typing import List, Tuple, Dict, Any
import pandas as pd
import os
from collections import defaultdict


try:
    MONTHLY_SCORES_DF = pd.read_csv(
        os.path.join(DATA_PATH, "monthly_scores.csv"))
    MONTHLY_SCORES_DF["symbol"] = MONTHLY_SCORES_DF["symbol"].astype(
        "category")
    MONTHLY_CACHE = defaultdict(pd.DataFrame)
    for (m, y), df in MONTHLY_SCORES_DF.groupby(["month", "year"]):
        MONTHLY_CACHE[(m, y)] = df.set_index("symbol")
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

    @staticmethod
    def normalize_columns(df: pd.DataFrame, columns: List[str]
                          ) -> pd.DataFrame:
        min_vals = df[columns].min()
        max_vals = df[columns].max()
        diff = max_vals - min_vals
        normalized = df[columns].sub(min_vals).div(diff.where(diff != 0, 1))
        return normalized.fillna(0)

    def get_all_scores(self) -> pd.DataFrame:
        """
        Retrieve and merge institutional and financial scores for all symbols.
        If any scores are missing, set them to 0.
        """
        df = MONTHLY_CACHE.get((self.month, self.year))
        self.symbols = list(
            set(self.symbols).intersection(df.index.tolist())
        )
        if df is not None:
            return df.loc[self.symbols].reset_index().copy()
        # Empty if no match
        return pd.DataFrame(columns=MONTHLY_SCORES_DF.columns)

    def calculate_institutional_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the institutional score based on fund net buying, number of fund holdings, and net fund change.
        """
        # Normalize columns
        columns = ["fund_net_buying",
                   "number_fund_holdings", "net_fund_change"]
        df[columns] = StocksRanking.normalize_columns(df, columns)
        # Calculate institutional score
        net_fund_change_w = 1.0 - \
            self.params["fund_net_buying"] - \
            self.params["number_fund_holdings"]
        assert net_fund_change_w >= 0.0, (
            f"Invalid weight for net fund change: {net_fund_change_w}"
        )
        df["inst_score"] = (
            self.params["fund_net_buying"] * df["fund_net_buying"]
            + self.params["number_fund_holdings"] * df["number_fund_holdings"]
            + net_fund_change_w * df["net_fund_change"]
        ).fillna(0).clip(lower=0)
        # log error if any score is greater than 1.0
        if (df["inst_score"] > 1.0).any():
            logger.error(
                f"Invalid institutional score:\n{df[df['inst_score'] > 1.0][[
                    'symbol', 'inst_score', 'fund_net_buying',
                    'number_fund_holdings', 'net_fund_change'
                ]].to_string()}"
            )
            logger.info(
                f"Weights: {self.params['fund_net_buying']}, "
                f"{self.params['number_fund_holdings']}, "
                f"{net_fund_change_w}"
            )

    def calculate_fin_score(self, df: pd.DataFrame) -> None:
        """
        Calculate the financial score (fin_score) based on ROE, PE, revenue growth, and debt-to-equity ratio.
        """
        df["debt_to_equity"] = df["debt_to_equity"].clip(lower=0.0, upper=2.0)
        df["pe_score"] = (
            (df["revenue_growth"] - df["pe"]) / df["revenue_growth"]
        ).clip(lower=0.0)

        # Normalize columns
        columns = ["roe", "revenue_growth", "debt_to_equity", "pe_score"]
        df[columns] = StocksRanking.normalize_columns(df, columns)

        # Calculate financial score
        de_weight = 1.0 - self.params["roe"] - \
            self.params["revenue_growth"] - self.params["pe"]
        if abs(de_weight) < 1e-6:
            de_weight = 0.0
        assert de_weight >= 0.0, (
            f"Invalid weight for debt-to-equity: {de_weight}"
            f" (roe: {self.params['roe']}, "
            f"revenue_growth: {self.params['revenue_growth']}, "
            f"pe: {self.params['pe']})"
        )
        df["fin_score"] = (
            self.params["roe"] * df["roe"]
            + self.params["revenue_growth"] * df["revenue_growth"]
            + de_weight * df["debt_to_equity"]
            + self.params["pe"] * df["pe_score"]
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
        top_stocks = df.nlargest(self.params["number_of_stocks"], "score")[
            ["symbol", "score"]].values.tolist()

        logger.debug(
            f"Institutional and financial scores:\n"
            f"{df[['symbol', 'inst_score', 'fin_score', 'score']]
               .head(10).to_string(index=False)}"
        )

        # Return the top-ranked symbols with their scores
        return top_stocks
