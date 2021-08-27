import os
from os import path
import logging
import argparse
import boto3
from decimal import Decimal

import utils
from repository import initialize_db, load_metric, clean_machine_metrics, Metric


logging.info('Starting machine data ingestion!')

utils.configure_logging()

logging.info('Initializing database...')
initialize_db()

parser = argparse.ArgumentParser(description='Ingest machine timeseries')
parser.add_argument('-d', '--data-dir', default='',
                    help='Path to directory with machine CSV data')
args = parser.parse_args()

data_dir_path = args.data_dir

if not utils.validate_data_dir_path(data_dir_path):
    exit(1)

logging.info('Loading data from directory {}'.format(data_dir_path))
data_files = utils.get_files_in_dir(data_dir_path)

for data_file in data_files:
    machine_name = os.path.basename(data_file).replace('.csv', '')
    reader = utils.create_machine_data_reader(data_file)

    for datum in reader:

        timestamp = datum[0]
        data = [Decimal(value) for value in datum[1:]]
        metric = Metric(machine_name, timestamp, data)

        if timestamp == '' or timestamp is None:
            continue

        load_metric(metric)

logging.info('Cleaning machine data...')
clean_machine_metrics()

logging.info('Machine data ingest complete!')
