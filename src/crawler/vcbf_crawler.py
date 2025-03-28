import os
import requests
from bs4 import BeautifulSoup
import time
import unicodedata
import json
import argparse
import yaml
from tqdm import tqdm
import pandas as pd
from typing import Tuple
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class VCBFCrawler():
    """
    Note: the date in the result is the corresponding period data date, not the
    release date
    """
    VCBF_STATEMENTS_URL = ("https://www.vcbf.com/quan-he-nha-dau-tu/bao-cao-cua-cac-quy-mo"
                           "/bao-cao-tai-chinh-vcbf/")
    # VCBF fund crawler
    VCBF_FUNDS = ["VCBF-TBF", "VCBF-MGF", "VCBF-FIF", "VCBF-BCF"]
    VCBF_URL = "https://www.vcbf.com/"
    DOWNLOAD_DIR = "downloaded"
    EXTRACT_DIR = "extracted"
    SHEET_NAME = "BCDanhMucDauTu_06029"

    def __init__(self):
        with open("../../config/config.yaml", "r") as f:
            self.COOL_DOWN = yaml.safe_load(f)["crawler_cool_down"]

    def get_financial_statement_links(self, save_dir):
        page = 1
        files = []
        stop = False
        while not stop:
            print(f"Page: {page}")
            process_url = self.VCBF_STATEMENTS_URL + "?p=" + str(page)
            print(f"Processing URL: {process_url}")
            response = requests.get(process_url)
            if response.status_code != 200:
                print("Failed to fetch page")
                break
            print(f"Fetching page {page}")
            soup = BeautifulSoup(response.text, 'html.parser')
            reports = soup.find_all('div', class_='list-download')
            if not reports:
                print("No reports found")
                break
            print(f"Found {len(reports)} reports")
            for report in reports:
                title = report.find('p').text.strip()
                normalized_title = unicodedata.normalize("NFC", title)
                # print(normalized_title)
                prefix = u"Báo cáo tháng"
                if not normalized_title.startswith(prefix):
                    continue
                download_link = report.find('a', class_='cta-download')['href']
                if not download_link.endswith((".xlsx", ".rar")):
                    print("Not an Excel or Rar file", download_link)
                    stop = True
                    break
                print(
                    f"Title: {normalized_title}, Download Link: {download_link}")
                files.append({
                    "title": normalized_title,
                    "download_link": download_link
                })
            page += 1
            time.sleep(self.COOL_DOWN)
        with open(os.path.join(save_dir, "VCBF.json"), "w", encoding="utf-8") as f:
            json.dump(files, f, indent=4, ensure_ascii=False)
        print("Saved to VCBF.json")

    def download_files(self, save_dir):
        with open(os.path.join(save_dir, "VCBF.json"), "r", encoding="utf-8") as f:
            files = json.load(f)

        if not os.path.exists(f"{save_dir}/{self.DOWNLOAD_DIR}"):
            os.makedirs(f"{save_dir}/{self.DOWNLOAD_DIR}")

        for file in tqdm(files):
            title = file["title"].replace("/", "-")
            download_link = self.VCBF_URL + file["download_link"]
            file_name = title + ".xlsx"
            response = requests.get(download_link)
            with open(os.path.abspath(f"{save_dir}/{self.DOWNLOAD_DIR}/{file_name}"), "wb") as f:
                f.write(response.content)
            time.sleep(self.COOL_DOWN)

        print("Downloaded all files")

    def get_financial_statements(self, save_dir):
        self.get_financial_statement_links(save_dir)
        self.download_files(save_dir)
        self.extract_all_data(save_dir)
        self.merge_files(save_dir)

    def extract_all_data(self, save_dir):
        for file in os.listdir(f"{save_dir}/{self.DOWNLOAD_DIR}"):
            if file.endswith(".xlsx"):
                print(f"Extracting data from {file}...")
                try:
                    self.extract_data(f"{save_dir}/{self.DOWNLOAD_DIR}/{file}",
                                      f"{save_dir}/{self.EXTRACT_DIR}")
                except Exception as e:
                    print(f"Failed to extract data from {file}: {
                        e}")
        print("Extracted all data")

    def extract_data(self, file, save_dir):
        df = pd.read_excel(file, sheet_name=self.SHEET_NAME)

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
            'Category|Quantity|Market price|Value|total asset', case=False, na=False)]
        section_df = section_df.dropna()
        section_df.columns = ['Category', 'Quantity',
                              'Market Price', 'Value', 'Total Asset Ratio']

        # Display the extracted section
        print(section_df.head())
        print(section_df.shape)

        # save to csv
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        section_df.to_csv(f"{save_dir}/{file.split("/")[-1]}.csv", index=False)

    def extract_date_symbol(self, file: str) -> Tuple[datetime, str]:
        """
        Extract the date and symbol from the file name
        Example: "Báo cáo tháng 01-2023 - Quỹ VCBF-BCF.xlsx" -> (datetime(2023, 1, 1), "VCBF-BCF")
        """
        file = file.split("/")[-1]

        # Extract the date
        date_str = file.split("tháng")[1].split("-")[0].strip()
        month, year = int(date_str), int(
            file.split("-")[1].split(".")[0].strip())
        date = datetime(year, month, 1)

        # Extract the symbol
        symbol = "VCBF-" + file.split("-")[-1].split(".")[0].strip()
        return date, symbol

    def merge_files(self, save_dir):
        """
        Merge all extracted files into a single JSON file
        """
        files = os.listdir(f"{save_dir}/{self.EXTRACT_DIR}")
        columns = ['Fund Code', 'Date', 'Category', 'Quantity',
                   'Market Price', 'Value', 'Total Asset Ratio']
        merged_df = pd.DataFrame()
        merged_df = merged_df.reindex(columns=columns)

        for file in files:
            df = pd.read_csv(f"{save_dir}/{self.EXTRACT_DIR}/{file}")
            # skip empty files
            if df.empty or df.isna().all().all():
                print(f"Skipping empty file: {file}")
                continue
            date, symbol = self.extract_date_symbol(file)
            df['Date'] = date
            df['Fund Code'] = symbol
            merged_df = pd.concat([merged_df, df], ignore_index=True)

        merged_df.to_csv(f"{save_dir}/fund_portfolios.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_dir", type=str,
                        default=os.getenv("DATA_PATH", "."))
    parser.add_argument("--operation", type=str,
                        default="all")
    args = parser.parse_args()
    save_dir = f"../../{args.save_dir}/VCBF"

    crawler = VCBFCrawler()
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    if args.operation == "get_financial_statement_links":
        crawler.get_financial_statement_links(save_dir)
    elif args.operation == "download_files":
        crawler.download_files(save_dir)
    elif args.operation == "all":
        crawler.get_financial_statements(save_dir)
    elif args.operation == "extract_data":
        crawler.extract_all_data(save_dir)
    elif args.operation == "merge_files":
        crawler.merge_files(save_dir)
    else:
        print("Invalid operation")
