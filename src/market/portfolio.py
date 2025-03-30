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
        self.realized_profit_loss = 0.0
        # Format: {asset_name: {'quantity': float, 'average_price': float}},
        # average price is average amount of money spent to buy the asset
        # (included transaction fee)
        self.assets = {}
        self.transactions = []

    def add_asset(self, asset_name: str, quantity: float, total_cost: float, price: float, transaction_date: datetime):
        """
        Add an asset to the portfolio.
        """
        if asset_name not in self.assets:
            self.assets[asset_name] = {
                'quantity': quantity, 'average_price': total_cost / quantity}
        else:
            current_quantity = self.assets[asset_name]['quantity']
            current_avg_price = self.assets[asset_name]['average_price']
            new_quantity = current_quantity + quantity
            # Update the average price
            new_avg_price = (current_quantity * current_avg_price +
                             total_cost) / new_quantity
            self.assets[asset_name]['quantity'] = new_quantity
            self.assets[asset_name]['average_price'] = new_avg_price
        self.balance -= total_cost
        self.transactions.append({
            'action': 'buy',
            'asset': asset_name,
            'quantity': quantity,
            'price': price,
            'total_cost': total_cost,
            'datetime': transaction_date
        })

    def remove_asset(self, asset_name: str, quantity: float, total_revenue: float, price: float, transaction_date: datetime):
        """
        Remove an asset from the portfolio.
        """
        if asset_name in self.assets:
            current_quantity = self.assets[asset_name]['quantity']
            average_price = self.assets[asset_name]['average_price']
            if quantity > current_quantity:
                raise ValueError(
                    f"Not enough quantity of {asset_name} to sell. Available: {current_quantity}, Requested: {quantity}")

            # Calculate realized profit/loss
            realized_pl = total_revenue - (quantity * average_price)
            self.realized_profit_loss += realized_pl

            # Update the asset quantity
            self.assets[asset_name]['quantity'] -= quantity
            if self.assets[asset_name]['quantity'] <= 0:
                del self.assets[asset_name]

            # Update the balance
            self.balance += total_revenue

            # Log the transaction
            self.transactions.append({
                'action': 'sell',
                'asset': asset_name,
                'quantity': quantity,
                'price': price,
                'total_revenue': total_revenue,
                'realized_pl': realized_pl,
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
            'Quantity': [self.assets[asset]['quantity'] for asset in self.assets],
            'Average Price': [self.assets[asset]['average_price'] for asset in self.assets],
            'Balance': self.balance,
            'Realized P/L': self.realized_profit_loss,
            'Transactions': [str(t) for t in self.transactions]
        }
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
