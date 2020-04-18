from src.utils.debug import Debug
from src.exchange.orders.order_utils import Exectype, Direction, OrderStatus
from src.exchange.orders.order import Order
import pandas as pd


class OrderCreator(Debug):
    """
    Auxiliary class, used to create orders in tests
    """
    required_columns = ['creator_id', 'contract', 'creation_time', 'order_id', 'direction',
                        'exec_type', 'price', 'size', 'expiration_time']

    map_exec_type = {elem.value: elem for elem in Exectype}
    map_direction = {elem.value: elem for elem in Direction}

    map_exec_type_identity = {elem: elem for elem in Exectype}
    map_direction_identity = {elem: elem for elem in Direction}

    @classmethod
    def get_direction(cls, direction):
        """
        ...
        :param direction:
        :return:
        """
        if direction in cls.map_direction:
            return cls.map_direction[direction]
        elif direction in cls.map_direction_identity:
            return cls.map_direction_identity[direction]
        else:
            raise Exception('Error: %s' % str(cls.map_direction))

    @classmethod
    def get_exec_type(cls, exec_type):
        if exec_type in cls.map_exec_type:
            return cls.map_exec_type[exec_type]
        elif exec_type in cls.map_exec_type_identity:
            return cls.map_exec_type_identity[exec_type]
        else:
            raise Exception('Error')

    @classmethod
    def create_order_as_series(cls, row):
        assert (set(row.keys()) == set(cls.required_columns))
        creator_id = row['creator_id']
        creation_time = row['creation_time']
        order_id = row['order_id']
        price = row['price']
        size = row['size']
        direction = cls.get_direction(row['direction'])
        exec_type = cls.get_exec_type(row['exec_type'])
        expiration_time = row['expiration_time']
        contract = row['contract']
        return pd.Series([Order(creator_id, contract, creation_time, order_id, price, size, direction=direction,
                                exec_type=exec_type,
                                expiration_time=expiration_time, status=OrderStatus.Created)])

    @classmethod
    def create_order_from_dict(cls, d):
        set1 = sorted(list(d.keys()))
        set2 = sorted(cls.required_columns)
        assert(str(set1) == str(set2))

        creator_id = d['creator_id']
        creation_time = d['creation_time']
        order_id = d['order_id']
        price = d['price']
        size = d['size']
        direction = cls.get_direction(d['direction'])
        exec_type = cls.get_exec_type(d['exec_type'])
        expiration_time = d['expiration_time']
        contract = d['contract']
        return Order(creator_id, contract, creation_time, order_id, price, size,
                     direction=direction,
                     exec_type=exec_type,
                     expiration_time=expiration_time,
                     status=OrderStatus.Created)
