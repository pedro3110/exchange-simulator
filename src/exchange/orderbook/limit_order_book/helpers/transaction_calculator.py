from src.exchange.orders.order_utils import Exectype
from src.utils.debug import Debug
import numpy as np


class TransactionCalculator(Debug):

    def get_price_executed(self, bid, ask):
        """
        Determines the price at which a transaction executes. It follows the rules:
        - price(bid) == price(ask) => same price
        - else if bid=Limit & ask=Limit => price of the oldest order (or of the order with bigger size)
        :param bid: Order
        :param ask: Order
        :return: float
        """
        if bid.get_exec_type() is Exectype.Limit and ask.get_exec_type() is Exectype.Limit:
            # Limit vs. Limit
            assert(bid.price >= ask.price)
            if bid.price == ask.price:
                return bid.price
            else:
                # Both orders are Limit orders. Use the price of the one that was accepted first
                if bid.accept_time != ask.accept_time:
                    return bid.price if bid.accept_time < ask.accept_time else ask.price
                elif bid.size != ask.size:
                    # Both where accepted exactly at the same time. Use the price of the order with the bigger size
                    return ask.price if bid.size < ask.size else bid.price
                else:
                    # If same accepted time and same size, use the mean price (set arbitrarily)
                    return np.mean([bid.price, ask.price])
        elif bid.get_exec_type() in [Exectype.Limit, Exectype.Market] and ask.get_exec_type() in [Exectype.Limit, Exectype.Market]:
            # Limit vs. Market or Market vs. Limit or Market vs. Market
            if bid.get_exec_type() is Exectype.Market and ask.get_exec_type() is Exectype.Market:
                # Market vs. Market
                raise Exception('A price for matching two market orders should never be required')
            else:
                # Market vs. Limit & Limit vs. Market. Execute at the price of the limit order
                return bid.price if bid.get_exec_type() is Exectype.Limit else ask.price
        else:
            raise Exception('Only Limit vs. Market orders can be matched by price')

    def get_size_executed(self, bid, ask):
        """
        Determines the number of contracts that are executed in a transaction
        :param bid: Order
        :param ask: Order
        :return: Integer
        """
        return bid.size_remaining if bid.size_remaining < ask.size_remaining else ask.size_remaining
