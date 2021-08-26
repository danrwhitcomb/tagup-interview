
import boto3
import psycopg2.pool

_conn_pool = psycopg2.pool.SimpleConnectionPool(
    1, 1, host='postgres', database='tagup', user='user', password='password')


def with_connection(function):

    def execute(*args, **kwargs):
        conn = _conn_pool.getconn()
        function(conn, *args, **kwargs)
        conn.commit()
        _conn_pool.putconn(conn)

    return execute


@with_connection
def initialize_db(conn):
    cursor = conn.cursor()
    cursor.execute('''create table if not exists machine_metrics (
                        machine_name varchar(64) not null,
                        time timestamp not null,
                        metric_1 double precision,
                        metric_2 double precision,
                        metric_3 double precision
                    );''')

    cursor.execute('''
        alter table machine_metrics add constraint machine_name_timestamp_constraint UNIQUE (machine_name, time);
    ''')

    cursor.execute('''
        create index if not exists machine_metrics_machine_idx
        on machine_metrics
        (machine_name, time desc);
    ''')


class Metric:

    def __init__(self, machine_name: str, timestamp: str, data):
        self.machine_name = machine_name
        self.timestamp = timestamp
        self.data = data


@with_connection
def load_metric(conn, metric: Metric):

    cursor = conn.cursor()
    cursor.execute('''
        insert into machine_metrics (machine_name, time, metric_1, metric_2, metric_3)
        values (%(name)s, %(time)s, %(metric_1)s, %(metric_2)s, %(metric_3)s)
        on conflict (machine_name, time) do update set metric_1 = %(metric_1)s, metric_2 = %(metric_2)s, metric_3 = %(metric_3)s
    ''', {
        'name': metric.machine_name,
        'time': metric.timestamp,
        'metric_1': metric.data[0],
        'metric_2': metric.data[1],
        'metric_3': metric.data[2]
    })
