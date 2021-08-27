
import boto3
import psycopg2.pool
from collections import namedtuple

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
                        metric_3 double precision,
                        metric_4 double precision
                    );''')

    cursor.execute('''
        alter table machine_metrics drop constraint if exists machine_name_timestamp_constraint;
    ''')

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


IqrRange = namedtuple('IqrRange', ['min', 'max'])


@with_connection
def load_metric(conn, metric: Metric):

    with conn.cursor() as cursor:
        cursor.execute('''
            insert into machine_metrics (machine_name, time, metric_1, metric_2, metric_3, metric_4)
            values (%(name)s, %(time)s, %(metric_1)s, %(metric_2)s, %(metric_3)s, %(metric_4)s)
            on conflict (machine_name, time) do update set metric_1 = %(metric_1)s, metric_2 = %(metric_2)s, metric_3 = %(metric_3)s, metric_4 = %(metric_4)s
        ''', {
            'name': metric.machine_name,
            'time': metric.timestamp,
            'metric_1': metric.data[0],
            'metric_2': metric.data[1],
            'metric_3': metric.data[2],
            'metric_4': metric.data[3]
        })


@with_connection
def clean_machine_metrics(conn):
    cursor = conn.cursor()

    # I'm fairly certain theres a cleaner way to do this,
    # but this works at least

    with conn.cursor() as cursor:
        _clear_outliers(cursor, 'metric_1')
        _clear_outliers(cursor, 'metric_2')
        _clear_outliers(cursor, 'metric_3')
        _clear_outliers(cursor, 'metric_4')


def _clear_outliers(cursor, metric):
    iqrs = _get_iqr_ranges(cursor, metric)

    for machine, iqr in iqrs.items():
        cursor.execute('''
            update machine_metrics
            set {metric} = null
            where machine_name = %(machine)s and (
                {metric} > %(max)s or
                {metric} < %(min)s
            )
        '''.format(metric=metric), {
            'min': iqr.min,
            'max': iqr.max,
            'machine': machine,
        })


def _get_iqr_ranges(cursor, metric):
    cursor.execute('''
    select
        machine_name,
        m.{metric}_fq - ((m.{metric}_tq - m.{metric}_fq) * 1.5) as {metric}_min,
        m.{metric}_tq + ((m.{metric}_tq - m.{metric}_fq) * 1.5) as {metric}_max

    from (
        select
            machine_name,
            percentile_disc(0.25) within group (order by {metric}) as {metric}_fq,
            percentile_disc(0.75) within group (order by {metric}) as {metric}_tq

        from machine_metrics
        where abs({metric}) > 1 and abs({metric}) < 225
        group by machine_name
    ) as m'''.format(metric=metric))

    return {row[0]: IqrRange(row[1], row[2]) for row in cursor}
