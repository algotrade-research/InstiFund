from src.settings import logger, DATA_PATH
import os
import pandas as pd
from datetime import datetime  # Ensure correct import of datetime
import argparse


def get_vnindex_benchmark(start_date: datetime, end_date: datetime
                          ) -> pd.DataFrame:
    """
    Get VNINDEX benchmark data from vnstock API.
    """
    from src.settings import vnstock
    logger.debug(
        f"Fetching VNINDEX benchmark data from {start_date} to {end_date}.")
    vnindex = vnstock.quote.history(symbol="VNINDEX",
                                    start=start_date.strftime("%Y-%m-%d"),
                                    end=end_date.strftime("%Y-%m-%d"))
    vnindex = vnindex[["time", "close"]].copy()
    vnindex.rename(columns={
        "time": "datetime",
        "close": "total_assets"}, inplace=True)
    vnindex["datetime"] = pd.to_datetime(vnindex["datetime"])
    # Ensure sorted by datetime
    vnindex.sort_values(by="datetime", inplace=True)
    vnindex.set_index("datetime", inplace=False,
                      drop=False)  # Keep `datetime` column
    logger.debug(
        f"VNINDEX benchmark data fetched successfully with {len(vnindex)} rows.")
    return vnindex


def eval_vnindex(start_date: datetime, end_date: datetime,
                 result_dir: str = None):
    """
    Evaluate VNINDEX performance between the given time range and save the results.

    :param start_date: Start date of the evaluation period.
    :param end_date: End date of the evaluation period.
    :param result_dir: Directory to save the evaluation results. If None, it will be auto-set.
    """
    from src.evaluate import Evaluate

    # Auto-set result_dir if not provided
    if result_dir is None:
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        result_dir = os.path.join(DATA_PATH, "vnindex", date_range)

    # Fetch VNINDEX data
    vnindex_data = get_vnindex_benchmark(start_date, end_date)
    logger.info(
        f"Columns: {vnindex_data.columns}"
    )

    # Prepare the result directory
    os.makedirs(result_dir, exist_ok=True)

    # Create an Evaluate instance for VNINDEX
    evaluator = Evaluate(vnindex_data, name="vnindex")

    # Save evaluation results and plots
    evaluator.evaluate(result_dir)

    logger.info(f"VNINDEX evaluation results saved to {result_dir}.")


def main():
    """
    Main function to evaluate VNINDEX performance using command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Evaluate VNINDEX performance.")
    parser.add_argument("--start_date", type=str, required=True,
                        help="Start date of the evaluation period (format: YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, required=True,
                        help="End date of the evaluation period (format: YYYY-MM-DD).")
    parser.add_argument("--result_dir", type=str, default=None,
                        help="Directory to save the evaluation results. If not provided, it will be auto-set.")
    args = parser.parse_args()

    # Parse dates
    start_date = datetime.strptime(
        args.start_date, "%Y-%m-%d")  # Correct usage
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")  # Correct usage

    # Run evaluation
    eval_vnindex(start_date, end_date, result_dir=args.result_dir)


if __name__ == "__main__":
    main()
