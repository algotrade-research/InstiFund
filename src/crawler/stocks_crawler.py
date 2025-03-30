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

    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        logger.info(
            f"Starting data retrieval for range: {start_date} to {end_date}.")
        data = get_daily_data(start_date, end_date)
        if data.empty:
            logger.warning("No data found for the given date range.")
        else:
            logger.info("Data retrieved successfully. Saving to CSV.")
            print(data.head())
            # Save to CSV
            csv_path = os.path.join(DATA_PATH, "daily_data.csv")
            data.to_csv(csv_path, index=False)
            logger.info(f"Data saved to {csv_path}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
