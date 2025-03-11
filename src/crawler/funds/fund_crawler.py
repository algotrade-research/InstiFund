import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod

# Fund crawler by fund company


class FundCrawler(ABC):
    def __init__(self, fund_list, url):
        self.fund_list = fund_list
        self.url = url
        self.html = requests.get(self.url).text
        self.soup = BeautifulSoup(self.html, "html.parser")

    @abstractmethod
    def get_financial_statements(self):
        pass
