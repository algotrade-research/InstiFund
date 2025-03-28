from src.settings import DATA_PATH
import pandas as pd
from typing import List

PYTHONPATH = '..'

# temporary for VCBF funds
FUND_DF = pd.read_json(DATA_PATH + "/VCBF/fund_portfolios.csv")


def get_stocks_list() -> List[str]:
    """
    Get the list of stock symbols
    """
    return FUND_DF["Category"].unique().tolist()
