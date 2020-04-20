import sys
root_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/src/'
example_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/examples/cda/'
example_path_logs = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/examples/cda/logs/'
sys.path.append(root_path)
sys.path.append(example_path)

from utils.config import get_logger
import logging
log_dirname = example_path_logs + 'experiment_2.log'

formatter = logging.Formatter('%(message)s')
logger = get_logger('experiment_2', log_dirname, formatter)

# Clean log
with open(log_dirname, 'w+') as f:
    f.truncate()

"""
Test Limit Order Book.
Use agents_data/history_ibm_1.csv
"""
import pandas as pd
from tabulate import tabulate

orders_filename = example_path + 'agents_data/history_ibm_1.csv'
orders = pd.read_csv(orders_filename, index_col=False)
logger.debug('Bid/Ask table read')
logger.debug(tabulate(orders.head(), headers='keys', tablefmt='psql'))

from system_components.helpers.order import OrderCreator

# Create orders
orders['order'] = orders.apply(OrderCreator.create_order_as_series, 1)
orders = orders['order'].tolist()

# Initialize Bid Ask Table
from system_components.helpers.orderbook.lobtable import LOBTable
contract = 'IBM'
ba_table = LOBTable(contract=contract)

# Send orders to BAT
for i, order in enumerate(orders):
    logger.debug(order)
    ba_table.handle_order(order, current_time=order.creation_time)
