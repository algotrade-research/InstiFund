from vcbf_crawler import VCBFCrawler
import pandas as pd
import os

FOLDER = "../../../../data/VCBF"
INPUT_DIR = FOLDER + "/downloaded"
SAVE_DIR = FOLDER + "/extracted"
SHEET_NAME = "BCDanhMucDauTu_06029"


def extract_data(FILE):
    df = pd.read_excel(FILE, sheet_name=SHEET_NAME)

    # Extract all rows containing the specified text in any column
    keyword = "STT"
    matches = df[df.apply(lambda row: row.astype(str).str.contains(
        keyword, case=False, na=False).any(), axis=1)]

    # Display the extracted rows
    columns = []
    for i in range(len(df.columns)):
        columns.append(df.iloc[matches.index[0], i])
    print(columns)

    keyword = "CỔ PHIẾU NIÊM YẾT"
    matches = df[df.apply(lambda row: row.astype(str).str.contains(
        keyword, case=False, na=False).any(), axis=1)]

    start_row = matches.index[0] + 2

    # Extract all rows under the specified section until an empty row or a new section is detected
    section_data = []
    for i in range(start_row, len(df)):
        row = df.iloc[i]
        # Stop if we encounter an empty row or a new section header
        if row.isna().iloc[0] or "TOTAL" in str(row.iloc[1]).upper():
            break
        section_data.append(row)

    if section_data == []:
        raise "No data found in the specified section"

    # Convert the extracted data to a DataFrame for better readability
    section_df = pd.DataFrame(section_data)
    section_df.reset_index(drop=True, inplace=True)
    section_df.columns = columns

    # keep column contain "Category" or "Value" or "total asset"
    section_df = section_df.loc[:, section_df.columns.str.contains(
        'Category|Value|total asset', case=False, na=False)]
    section_df = section_df.dropna()
    section_df.columns = ['Category', 'Value', 'Total Asset Ratio']

    # Display the extracted section
    print(section_df.head())
    print(section_df.shape)

    # save to csv
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    section_df.to_csv(f"{SAVE_DIR}/{FILE.split("/")[-1]}.csv", index=False)


if __name__ == "__main__":
    for file in os.listdir(INPUT_DIR):
        print(f"Extracting data from {file}...")
        try:
            if file.endswith(".xlsx"):
                extract_data(f"{INPUT_DIR}/{file}")
        except Exception as e:
            print(f"Error extracting data from {file}: {e}")
