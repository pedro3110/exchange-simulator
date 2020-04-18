class OBInformation:
    def __init__(self, contract, best_ask, best_bid):
        self.best_ask = best_ask
        self.best_bid = best_bid
        self.contract = contract

    def get_contract(self):
        return self.contract

    def get_best_ask_price(self):
        return self.best_ask.price if self.best_ask is not None else None

    def get_best_bid_ask_price_and_size(self):
        d = {'bid': None, 'ask': None}
        if self.best_bid is not None:
            d['bid'] = {
                'price': self.best_bid.price,
                'size': self.best_bid.size
            }
        if self.best_ask is not None:
            d['ask'] = {
                'price': self.best_ask.price,
                'size': self.best_ask.size
            }
        return d
