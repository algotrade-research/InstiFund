import os
import requests
from bs4 import BeautifulSoup
import time
import unicodedata
import json
import argparse
import yaml
from tqdm import tqdm


class VCBFCrawler():
    VCBF_STATEMENTS_URL = ("https://www.vcbf.com/quan-he-nha-dau-tu/bao-cao-cua-cac-quy-mo"
                           "/bao-cao-tai-chinh-vcbf/")
    # VCBF fund crawler
    VCBF_FUNDS = ["VCBF-TBF", "VCBF-MGF", "VCBF-FIF", "VCBF-BCF"]
    VCBF_URL = "https://www.vcbf.com/"

    def __init__(self):
        with open("../../../config/config.yaml", "r") as f:
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

        for file in tqdm(files):
            title = file["title"].replace("/", "-")
            download_link = self.VCBF_URL + file["download_link"]
            file_name = title + ".xlsx"
            response = requests.get(download_link)
            with open(os.path.abspath(save_dir + '/' + file_name), "wb") as f:
                f.write(response.content)
            time.sleep(self.COOL_DOWN)

        print("Downloaded all files")

    def get_financial_statements(self, save_dir):
        self.get_financial_statement_links(save_dir)
        self.download_files(save_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_dir", type=str, default=".")
    parser.add_argument("--operation", type=str,
                        default="get_financial_statements")
    args = parser.parse_args()

    crawler = VCBFCrawler()
    if not os.path.exists(args.save_dir):
        os.mkdir(args.save_dir)

    if args.operation == "get_financial_statement_links":
        crawler.get_financial_statement_links(args.save_dir)
    elif args.operation == "download_files":
        crawler.download_files(args.save_dir)
    elif args.operation == "get_financial_statements":
        crawler.get_financial_statements(args.save_dir)
    elif args.operation == "extract_data":
        crawler.extract_data(args.save_dir)
    else:
        print("Invalid operation")
