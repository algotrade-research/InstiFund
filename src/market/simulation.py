

class MarketSimulation:
    def __init__(self, market_data):
        self.market_data = market_data
        self.current_time = 0

    def step(self):
        # Simulate a single time step in the market
        if self.current_time < len(self.market_data):
            data_point = self.market_data[self.current_time]
            self.current_time += 1
            return data_point
        else:
            raise StopIteration("End of market data reached.")