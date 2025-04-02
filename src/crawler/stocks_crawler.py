from src.settings import DATABASE, DATA_PATH, logger, vnstock, config
from src.recommendation.data import get_stocks_list
# from src.recommendation.stocks import USED_COLUMNS
import psycopg2
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import argparse
import time
import os

DAILY_QUERY = """
SELECT c.datetime, c.tickersymbol, c.price, d.quantity
FROM quote.close c
JOIN quote.dailyvolume d ON c.tickersymbol = d.tickersymbol
    AND c.datetime = d.datetime
WHERE c.datetime BETWEEN %s AND %s
    AND c.tickersymbol = ANY(%s)  -- Filter tickers using a list
ORDER BY c.datetime DESC
"""

# FINANCIAL_QUERY = """
# SELECT if.tickersymbol, if.year, if.quarter, it.name, if.value
# FROM financial.info if
# JOIN financial.item it ON if.code = it.code
# WHERE if.year BETWEEN %s AND %s
#     AND if.tickersymbol = ANY(%s)  -- Filter tickers using a list
#     AND it.name = ANY(%s)  -- Filter items using a list
# ORDER BY if.tickersymbol, if.year, if.quarter, it.name
# """


def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Execute a query and return the results as a list of dictionaries.
    """
    conn = None
    try:
        logger.debug(f"Executing query: {query} with params: {params}")
        conn = psycopg2.connect(
            dbname=DATABASE["NAME"],
            user=DATABASE["USER"],
            password=DATABASE["PASSWORD"],
            host=DATABASE["HOST"],
            port=DATABASE["PORT"]
        )
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(
            f"Query executed successfully. Retrieved {len(results)} rows.")
        return results
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return []
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed.")


# def get_last_close_price(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Retrieve the last close price of each stock at the end of each quarter.
#     """
#     df['quarter'] = df['datetime'].dt.to_period('Q') - 1
#     last_close_prices = df.sort_values(by=['datetime']).groupby(
#         ['tickersymbol', 'quarter']).last().reset_index()
#     last_close_prices = last_close_prices[['tickersymbol', 'quarter', 'price']]
#     last_close_prices.rename(
#         columns={'price': 'last_close_price'}, inplace=True)
#     return last_close_prices


def get_daily_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Get daily data from the database for the given date range.
    """
    logger.info(f"Fetching daily data from {start_date} to {end_date}.")
    if start_date > end_date:
        logger.error("Start date must be before end date.")
        raise ValueError("Start date must be before end date")

    stocks_list = get_stocks_list()
    if not stocks_list:
        logger.warning("No stocks found in the stock list.")
        return pd.DataFrame()

    query = DAILY_QUERY
    params = (start_date, end_date, stocks_list)
    results = execute_query(query, params)

    if not results:
        logger.warning("No data found for the given date range.")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df['datetime'] = pd.to_datetime(df['datetime'])
    logger.info(f"Data fetched successfully. Retrieved {len(df)} rows.")
    return df


def save_daily_data_to_csv(daily_data: pd.DataFrame):
    """
    Save daily data to a CSV file.
    """
    if daily_data.empty:
        logger.warning("No daily data to save.")
        return

    file_path = os.path.join(DATA_PATH, "daily_data.csv")
    daily_data.to_csv(file_path, index=False)
    logger.info(f"Daily data saved to {file_path}.")


# def get_financial_data(start_date: datetime, end_date: datetime, daily_data: pd.DataFrame) -> pd.DataFrame:
#     """
#     Retrieve financial data and add last close price.
#     If any stock is missing a column in USED_COLUMNS for a quarter, fill it with the previous quarter's value.
#     """
#     stocks_list = get_stocks_list()
#     if not stocks_list:
#         logger.warning("No stocks found in the stock list.")
#         raise ValueError("No stocks found in the stock list.")

#     logger.info(f"Stock list: {stocks_list}")

#     query = FINANCIAL_QUERY
#     params = (start_date.year, end_date.year, stocks_list, USED_COLUMNS)
#     financial_results = execute_query(query, params)

#     if not financial_results:
#         logger.warning("No financial data found for the given date range.")
#         return pd.DataFrame()

#     financial_df = pd.DataFrame(financial_results)
#     logger.info("Financial data retrieved successfully.")

#     return financial_df


# def fill_missing_financial_data(financial_df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Fill missing financial data for each stock and quarter using the previous quarter's values.
#     """
#     # Sort the financial data by tickersymbol, year, and quarter
#     financial_df.sort_values(
#         by=["tickersymbol", "year", "quarter"], inplace=True)

#     # Pivot the data to make it easier to work with
#     pivot_df = financial_df.pivot_table(
#         index=["tickersymbol", "year", "quarter"],
#         columns="name",
#         values="value",
#         aggfunc="first"
#     ).reset_index()

#     # Iterate through each stock and fill missing values
#     for column in USED_COLUMNS:
#         pivot_df[column] = pivot_df.groupby(
#             "tickersymbol")[column].fillna(method="ffill")

#     # Melt the data back to the original format
#     filled_df = pivot_df.melt(
#         id_vars=["tickersymbol", "year", "quarter"],
#         var_name="name",
#         value_name="value"
#     )

#     return filled_df

def get_financial_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Retrieve financial data for the given date range.
    """
    logger.info(f"Fetching financial data from {start_date} to {end_date}.")
    if start_date > end_date:
        logger.error("Start date must be before end date.")
        raise ValueError("Start date must be before end date")

    stocks_list = get_stocks_list()
    if not stocks_list:
        logger.warning("No stocks found in the stock list.")
        return pd.DataFrame()

    df = pd.DataFrame()
    for symbol in stocks_list:
        try:
            logger.info(f"Fetching income statement data for {symbol}.")
            income = vnstock.finance.income_statement(
                period="quarter", symbol=symbol, lang="en")
            income = income[[
                "Revenue (Bn. VND)", "yearReport", "lengthReport"]]
            time.sleep(config["crawler_cool_down"])

            logger.info(f"Fetching balance sheet data for {symbol}.")
            balance_sheet = vnstock.finance.balance_sheet(
                period="quarter", symbol=symbol, lang="en")
            balance_sheet = balance_sheet[[
                "Cash and cash equivalents (Bn. VND)", "LIABILITIES (Bn. VND)",
                "yearReport", "lengthReport"]]
            time.sleep(config["crawler_cool_down"])

            logger.info(f"Fetching ratio data for {symbol}.")
            ratio = vnstock.finance.ratio(
                period="quarter", symbol=symbol, lang="en")
            ratio = ratio[[("Chỉ tiêu định giá", "P/E"),
                           ("Chỉ tiêu khả năng sinh lợi", "ROE (%)"),
                           ("Chỉ tiêu thanh khoản", "Financial Leverage"),
                           ("Chỉ tiêu cơ cấu nguồn vốn", "Debt/Equity"),
                           ("Meta", "yearReport"),
                           ("Meta", "lengthReport")]]
            # flatten the multi-index columns
            ratio.columns = [
                col[1] if isinstance(col, tuple) else col
                for col in ratio.columns]

            logger.info(f"Merging financial data for {symbol}.")
            stock_df = pd.merge(income, balance_sheet, on=[
                "yearReport", "lengthReport"], how="outer")
            stock_df = pd.merge(stock_df, ratio, on=[
                "yearReport", "lengthReport"], how="outer")
            stock_df.rename(columns={
                "yearReport": "year",
                "lengthReport": "quarter",
                "Revenue (Bn. VND)": "Revenue",
                "Cash and cash equivalents (Bn. VND)": "Cash",
                "ROE (%)": "ROE",
                "LIABILITIES (Bn. VND)": "Liabilities",
            }, inplace=True)
            # Remove data not between start_date and end_date
            stock_df = stock_df[(stock_df["year"] >= start_date.year) &
                                (stock_df["year"] <= end_date.year)]
            stock_df["tickersymbol"] = symbol
            time.sleep(config["crawler_cool_down"])
            df = pd.concat([df, stock_df], ignore_index=True)
            save_financial_data_to_csv(df)
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {e}")
            continue

    return df


def save_financial_data_to_csv(financial_df: pd.DataFrame):
    """
    Save financial data to a CSV file.
    """
    if financial_df.empty:
        logger.warning("No financial data to save.")
        return

    file_path = os.path.join(DATA_PATH, "financial_data.csv")
    financial_df.to_csv(file_path, index=False)
    logger.info(f"Financial data saved to {file_path}.")


def main(start_date: datetime, end_date: datetime, action: str):
    """
    Main function to run the stocks crawler.
    """
    # Retrieve daily data
    if action == "daily" or action == "all":
        try:
            logger.info(
                f"Starting data retrieval for range: {start_date} to {end_date}.")
            daily_data = get_daily_data(start_date, end_date)
            save_daily_data_to_csv(daily_data)
        except Exception as e:
            logger.error(f"An error occurred while retrieving daily data: {e}")

    # Retrieve financial data
    if action == "financial" or action == "all":
        try:
            logger.info(
                f"Starting financial data retrieval for range: {start_date} to {end_date}.")
            financial_df = get_financial_data(start_date, end_date)
            save_financial_data_to_csv(financial_df)
        except Exception as e:
            logger.error(f"An error occurred while retrieving financial data: {e}")

    logger.info("Crawler finished running.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stocks Crawler for daily data")
    parser.add_argument("--start_date", type=str,
                        help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", type=str,
                        help="End date in YYYY-MM-DD format")
    parser.add_argument("--action", type=str,
                        choices=["daily", "financial", "all"],
                        help="Action to perform: daily or financial or both",
                        default="all")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

    main(start_date, end_date, args.action)
