from src.recommendation.scoring import StocksRanking
from src.recommendation.data import get_stocks_list
from src.market.simulation import MarketSimulation
from src.market.portfolio import Portfolio
from datetime import datetime
from src.utitlies import get_last_month
from src.settings import logger


def sell(portfolio, simulation, asset, quantity):
    sell_info = simulation.sell_stock(asset, quantity)
    if sell_info.get('total_revenue') is None:
        logger.warning(f"Failed to sell {asset}.")
        return False
    portfolio.remove_asset(
        asset, quantity, sell_info['total_revenue'], sell_info['date'])
    logger.debug(f"Sold {quantity} shares of {asset}.")
    return True


def buy(portfolio, simulation, symbol, quantity):
    buy_info = simulation.buy_stock(symbol, quantity)
    if buy_info.get('total_cost') is None:
        logger.warning(f"Failed to buy {symbol}.")
        return False
    portfolio.add_asset(
        symbol, quantity, buy_info['total_cost'], buy_info['date'])
    logger.debug(f"Bought {quantity} shares of {symbol}.")
    return True


if __name__ == '__main__':
    logger.info("Starting backtesting process.")
    stocks = get_stocks_list()
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    simulation = MarketSimulation(start_date, end_date)
    portfolio = Portfolio("Test Portfolio", 1000000)

    delay = False
    while True:
        if not simulation.step():
            logger.info("Simulation completed.")
            break

        # Get the current stock data
        current_data = simulation.get_current_stock_data()
        if current_data.empty:
            logger.debug("No market data available for the current date.")
            delay = True
            continue

        # If the current month is the end_date, sell all stocks
        if simulation.current_date.month == end_date.month and simulation.current_date.year == end_date.year:
            logger.info(
                "End of simulation period reached. Selling all stocks.")
            current_assets = list(portfolio.assets.keys())
            for asset in current_assets:
                quantity = portfolio.assets[asset]
                if not sell(portfolio, simulation, asset, quantity):
                    delay = True
                    continue
            logger.info("Final portfolio statistics:")
            logger.info(simulation.get_portfolio_statistics(portfolio))
            break

        # Rebalance the portfolio on the 8th day of each month
        if simulation.current_date.day == 8 or delay:
            delay = False
            logger.info(f"Rebalancing portfolio on {simulation.current_date}.")
            # Get the ranked stocks
            last_month, last_year = get_last_month(
                simulation.current_date.month, simulation.current_date.year)
            ranked_stocks = StocksRanking(
                last_month, last_year, stocks).get_ranking()

            # Select the top 5 stocks to rebalance
            top_stocks = [symbol for symbol, _ in ranked_stocks[:5]]
            logger.debug(f"Top 5 stocks for rebalancing: {top_stocks}")

            # Rebalance the portfolio
            current_assets = list(portfolio.assets.keys())

            # Sell stocks that are no longer in the top stocks
            for asset in current_assets:
                if asset not in top_stocks:
                    quantity = portfolio.assets[asset]
                    if not sell(portfolio, simulation, asset, quantity):
                        delay = True
                        continue

            # Buy new stocks that are in the top stocks but not in the portfolio
            for symbol in top_stocks:
                if symbol not in current_assets:
                    quantity = 10  # Example: Buy 10 shares of each new stock
                    if not buy(portfolio, simulation, symbol, quantity):
                        delay = True
                        continue

        # Log the portfolio statistics
        logger.debug("Current portfolio statistics:")
        logger.debug(simulation.get_portfolio_statistics(portfolio))
