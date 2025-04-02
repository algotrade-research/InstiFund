from src.recommendation.funds import InstitutionalScoring
from src.recommendation.stocks import FinancialScoring
from src.recommendation.data import get_stocks_list, FUND_DF, FINANCIAL_DF
from src.settings import logger, DATA_PATH

import pandas as pd
import os
from datetime import datetime


def main() -> None:
    """
    Preprocess the ratios and scores for stocks and funds.
    """
    # Get all symbols from the FUND_DF DataFrame
    symbols = get_stocks_list()

    start_year = min(FUND_DF["Date"].min().year, FINANCIAL_DF["year"].min())
    end_year = max(FUND_DF["Date"].max().year, FINANCIAL_DF["year"].max()) + 1
    start_date = datetime(year=start_year, month=1, day=1)
    end_date = datetime(year=end_year, month=12, day=31)

    logger.info(f"Symbols: {symbols}")
    logger.info(f"Start date: {start_date}, End date: {end_date}")

    # Iterate monthly from start_date to end_date
    current_date = start_date
    end_date = end_date.replace(day=1)  # Set to the first day of the month

    monthly_data = pd.DataFrame()
    while current_date <= end_date:
        last_month, last_year = current_date.month - 1, current_date.year
        if last_month == 0:
            last_month = 12
            last_year -= 1
        quarter = (current_date.month - 1) // 3 + 1
        last_quarter = quarter - 1 if quarter > 1 else 4
        last_quarter_year = current_date.year - \
            1 if last_quarter == 4 else current_date.year
        logger.info(f"Processing month: {current_date.month}, year: {current_date.year}\n"
                    f"Using institutional data from {last_month}/{last_year}\n"
                    f"and financial data from Q{last_quarter}/{last_quarter_year}")

        # Initialize scoring classes
        inst_scoring = InstitutionalScoring(last_month, last_year, symbols)
        fin_scoring = FinancialScoring(
            last_quarter, last_quarter_year, symbols)

        # Get scores for institutional and financial data
        inst_scores_df = inst_scoring.get_scores()
        fin_scores_df = fin_scoring.get_scores()

        if inst_scores_df.empty or fin_scores_df.empty:
            empty_df = []
            if inst_scores_df.empty:
                empty_df.append("institutional")
            if fin_scores_df.empty:
                empty_df.append("financial")
            logger.warning(
                f"Empty {empty_df} scores DataFrame for month "
                f"{current_date.month} year {current_date.year}. Skipping.")
            current_date = current_date.replace(
                day=1) + pd.DateOffset(months=1)
            continue

        # Merge scores DataFrames
        merged_df = pd.merge(inst_scores_df, fin_scores_df,
                             on="symbol", how="outer").fillna(0)
        merged_df["month"] = current_date.month
        merged_df["year"] = current_date.year
        logger.debug(
            f"Merged DataFrame: \n{merged_df.head(10).to_string(index=False)}")

        monthly_data = pd.concat([monthly_data, merged_df], ignore_index=True)

        # Move to the next month
        current_date = current_date.replace(
            day=1) + pd.DateOffset(months=1)

    # Save the merged DataFrame to a CSV file
    output_file = os.path.join(DATA_PATH, "monthly_scores.csv")
    df = pd.DataFrame(monthly_data)
    df.sort_values(by=["year", "month", "symbol"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_csv(output_file, index=False)
    logger.info(f"Scores saved to {output_file}")


if __name__ == "__main__":
    main()
