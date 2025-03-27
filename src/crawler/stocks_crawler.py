from vnstock import Vnstock


stock_source = Vnstock().stock(source='VCI')


def stocks_info():
    stocks = stock_source.listing.symbols_by_industries().head(20)
    print(stocks[['symbol', 'icb_name3']])


stocks_info()
