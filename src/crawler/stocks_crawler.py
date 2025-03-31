from src.settings import DATABASE, DATA_PATH, logger
from src.recommendation.data import get_stocks_list
import psycopg2
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import argparse
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

FINANCIAL_QUERY = """
SELECT if.tickersymbol, if.year, if.quarter, it.name, if.value
FROM financial.info if
JOIN financial.item it ON if.code = it.code
WHERE if.year BETWEEN %s AND %s
    AND if.tickersymbol = ANY(%s)  -- Filter tickers using a list
ORDER BY if.tickersymbol, if.year, if.quarter, it.name
"""


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


def get_last_close_price(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retrieve the last close price of each stock at the end of each quarter.
    """
    df['quarter'] = df['datetime'].dt.to_period('Q') - 1
    last_close_prices = df.sort_values(by=['datetime']).groupby(
        ['tickersymbol', 'quarter']).last().reset_index()
    last_close_prices = last_close_prices[['tickersymbol', 'quarter', 'price']]
    last_close_prices.rename(
        columns={'price': 'last_close_price'}, inplace=True)
    return last_close_prices


def get_daily_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Get daily data from the database for the given date range.
    """
    logger.info(f"Fetching daily data from {start_date} to {end_date}.")
    if start_date > end_date:
        logger.error("Start date must be before end date.")
        raise ValueError("Start date must be before end date")

    # Get the list of stocks to filter
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stocks Crawler for daily data")
    parser.add_argument("--start_date", type=str,
                        help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", type=str,
                        help="End date in YYYY-MM-DD format")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

    # Retrieve close price data
    try:
        logger.info(
            f"Starting data retrieval for range: {start_date} to {end_date}.")
        daily_data = get_daily_data(start_date, end_date)
        if daily_data.empty:
            logger.warning("No data found for the given date range.")
        else:
            logger.info("Daily data retrieved successfully.")
            print(daily_data.head())

            # Save to CSV
            daily_data.to_csv(os.path.join(
                DATA_PATH, "daily_data.csv"), index=False)
            logger.info("Daily data saved to CSV.")
    except Exception as e:
        logger.error(f"An error occurred while retrieving daily data: {e}")

    # Retrieve financial data and add last close price
    stocks_list = get_stocks_list()
    try:
        logger.info(
            f"Starting financial data retrieval for range: {start_date} to {end_date}.")
        if not stocks_list:
            logger.warning("No stocks found in the stock list.")
            raise ValueError("No stocks found in the stock list.")

        query = FINANCIAL_QUERY
        params = (start_date.year, end_date.year, stocks_list)
        financial_results = execute_query(query, params)

        if not financial_results:
            logger.warning("No financial data found for the given date range.")
        else:
            logger.info("Financial data retrieved successfully.")
            financial_df = pd.DataFrame(financial_results)

            # Add last close price as a new row for each stock and quarter
            logger.info("Calculating last close prices.")
            last_close_prices = get_last_close_price(daily_data)
            rows_to_add = []
            for _, row in last_close_prices.iterrows():
                rows_to_add.append({
                    "tickersymbol": row["tickersymbol"],
                    "year": row["quarter"].year,
                    "quarter": row["quarter"].quarter,
                    "name": "Last Close Price",
                    "value": row["last_close_price"]
                })

            # Convert rows_to_add to a DataFrame and concatenate with financial_df
            rows_to_add_df = pd.DataFrame(rows_to_add)
            financial_df = pd.concat(
                [financial_df, rows_to_add_df], ignore_index=True)

            # Save to CSV
            print(financial_df.head())
            financial_df.to_csv(os.path.join(
                DATA_PATH, "financial_data_with_close_price.csv"), index=False)
            logger.info("Financial data with last close price saved to CSV.")
    except Exception as e:
        logger.error(f"An error occurred while retrieving financial data: {e}")

    logger.info("Crawler finished running.")
