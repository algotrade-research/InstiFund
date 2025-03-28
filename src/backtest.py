from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list

if __name__ == '__main__':
    stocks = get_stocks_list()
    ranking = StocksRanking(1, 2023, stocks)
    print(ranking.recommend())
