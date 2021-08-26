import logging
import csv
import os
from os import path


def configure_logging():
    logging.basicConfig(format='%(levelname)s - %(asctime)-15s - %(message)s')


def validate_data_dir_path(data_dir_path):
    if not path.exists(data_dir_path):
        logging.error("Path {} not found".format(data_dir_path))
        return False

    if not path.isdir(data_dir_path):
        logging.error("Path {} is not a directory", format(data_dir_path))
        return False

    return True


def get_files_in_dir(base_dir):
    return [path.join(base_dir, f) for f in os.listdir(base_dir) if path.isfile(path.join(base_dir, f))]


def create_machine_data_reader(csv_path):
    with open(csv_path) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            yield row
