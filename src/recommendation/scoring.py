import datetime
from funds import get_institutional_score
from stocks import get_financial_score


def scoring_stock(dt: datetime, symbol: str) -> float:
    """
    Calculate the score of a stock based on its financial data 
    and institutional activities
    """
    # Institutional activities
    institutional_score = get_institutional_score(dt, symbol)

    # Financial data
    financial_score = get_financial_score(dt, symbol)

    return 0.6 * institutional_score + 0.4 * financial_score
