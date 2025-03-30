from datetime import datetime
import pandas as pd


class Portfolio:
    """
    A class to represent a portfolio of assets.
    Unit of balance is 1000 VND.
    """

    def __init__(self, name: str, initial_balance: float):
        self.name = name
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.assets = {}
        self.transactions = []

    def add_asset(self, asset_name: str, quantity: float, total_cost: float, transaction_date: datetime):
        """
        Add an asset to the portfolio.
        """
        if asset_name not in self.assets:
            self.assets[asset_name] = quantity
        else:
            self.assets[asset_name] += quantity
        self.balance -= total_cost
        self.transactions.append({
            'action': 'buy',
            'asset': asset_name,
            'quantity': quantity,
            'price': total_cost,
            'datetime': transaction_date
        })

    def remove_asset(self, asset_name: str, quantity: float, total_revenue: float, transaction_date: datetime):
        """
        Remove an asset from the portfolio.
        """
        if asset_name in self.assets:
            self.assets[asset_name] -= quantity
            if self.assets[asset_name] <= 0:
                del self.assets[asset_name]
            self.balance += total_revenue
            self.transactions.append({
                'action': 'sell',
                'asset': asset_name,
                'quantity': quantity,
                'price': total_revenue,
                'datetime': transaction_date
            })
        else:
            raise ValueError(f"Asset {asset_name} not found in portfolio.")

    def save_portfolio(self, file_path: str):
        """
        Save the portfolio to a CSV file.
        """
        data = {
            'Asset': list(self.assets.keys()),
            'Quantity': list(self.assets.values()),
            'Balance': self.balance,
            'Transactions': [str(t) for t in self.transactions]
        }
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
