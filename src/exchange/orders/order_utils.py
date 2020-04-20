from enum import Enum


class OrderStatus(Enum):
    """
    During all it's lifetime, each order must be in one of these states
    """
    Created = 0
    Submitted = 1
    Accepted = 2
    Partial = 3
    Complete = 4
    Rejected = 5
    Canceled = 6
    Expired = 7


class Exectype(Enum):
    """
    Each order has a specific Execution Type. The rules are:
        - Limit: It executes when the matching order has a price at least as good as the limit order price
        - Stop: It tracks the price of the underlying contract. When the underlying crosses this predefined entry point,
          the order becomes a Market order
        - StopLimit: It tracks the price of the underlying contract. When the underlying crosses this predefined entry
          point, the order becomes a Limit order that executes at a price at least as good as the predefined
        - Market: It executes at the best price that is available
    """
    Limit = 0
    Stop = 1
    StopLimit = 2
    Market = 3


class Direction(Enum):
    """
    To simplify things, we consider the cancelation of an order as a direction of a trade (kind of a second dimension)
    """
    Buy = 1
    Cancel = 0
    Sell = -1
