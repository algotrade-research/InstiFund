from src.recommendation.funds import InstitutionalScoring
from typing import List, Tuple
import pandas as pd


class StocksRanking:
    def __init__(self, month: int, year: int, symbols: List[str]):
        self.month = month
        self.year = year
        self.symbols = symbols

    def get_all_scores(self) -> pd.DataFrame:
        df_list = []  # Use a list to collect rows
        for symbol in self.symbols:
            scoring = InstitutionalScoring(self.month, self.year, symbol)
            (fund_net_buying, number_fund_holdings,
             net_fund_change) = scoring.get_scores()
            df_list.append({"symbol": symbol,
                            "fund_net_buying": fund_net_buying,
                            "number_fund_holdings": number_fund_holdings,
                            "net_fund_change": net_fund_change})
        # Use pd.DataFrame to create a DataFrame from the list of rows
        return pd.DataFrame(df_list)

    def normalize(self, df: pd.DataFrame, columns: List[str]) -> None:
        for column in columns:
            df[column] = (df[column] - df[column].min()) / \
                         (df[column].max() - df[column].min())

    def get_ranking(self) -> List[Tuple[str, float]]:
        df = self.get_all_scores()
        # Normalize all required columns at once
        self.normalize(
            df, ["fund_net_buying", "number_fund_holdings", "net_fund_change"])
        # Calculate the score
        df["score"] = 0.45 * df["fund_net_buying"] + \
            0.35 * df["number_fund_holdings"] + 0.2 * df["net_fund_change"]
        # Sort by score and return the symbols
        df = df.sort_values(by=["score"], ascending=False)
        df = df.reset_index(drop=True)
        # Return the top 3 symbols with their scores
        ranking = df[["symbol", "score"]].values.tolist()
        return ranking

    def recommend(self) -> List[str]:
        ranking = self.get_ranking()[:3]
        return ranking
