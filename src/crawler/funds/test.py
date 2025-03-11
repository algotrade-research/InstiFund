from vcbf_crawler import VCBFCrawler
import pandas as pd

FILE = "../../../../data/VCBF/Báo cáo tháng 01-2023 - Quỹ VCBF-TBF.xlsx"
SAVE_DIR = "../../../../data/VCBF"

# Load the specific sheet BCDanhMucDauTu_06029
sheet_name = 'BCDanhMucDauTu_06029'
df = pd.read_excel(FILE, sheet_name=sheet_name)

# Display the first few rows to understand its structure
df.head()

# Extract all rows containing the specified text in any column
keyword = "CỔ PHIẾU NIÊM YẾT, ĐĂNG KÝ GIAO DỊCH, CHỨNG CHỈ QUỸ NIÊM YẾT\nSHARES LISTED, SHARES REGISTERED FOR TRADING, LISTED FUND CERTIFICATES"
matches = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)]

# Display the extracted rows
matches


# Find the starting row for the specified section
start_row = matches.index[0] + 1

# Extract all rows under the specified section until an empty row or a new section is detected
section_data = []
for i in range(start_row, len(df)):
    row = df.iloc[i]
    # Stop if we encounter an empty row or a new section header
    if row.isna().all() or "PHỤ LỤC" in str(row[0]).upper():
        break
    section_data.append(row)

# Convert the extracted data to a DataFrame for better readability
section_df = pd.DataFrame(section_data)
section_df.reset_index(drop=True, inplace=True)

# Display the extracted section
section_df.head()


# Extract rows under the specified section based on non-empty stock codes in the second column (Unnamed: 1)
section_data = df.iloc[start_row:].dropna(subset=["Unnamed: 1"])

# Filter until an empty row or a new section is detected
filtered_section = []
for i, row in section_data.iterrows():
    if "PHỤ LỤC" in str(row[0]).upper() or row.isna().all():
        break
    filtered_section.append(row)

# Convert the extracted data to a DataFrame
filtered_section_df = pd.DataFrame(filtered_section).reset_index(drop=True)

# Display the extracted section
filtered_section_df.head()
