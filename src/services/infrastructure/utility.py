import pandas as pd
import ah_config
import ah_db
from ah_bank import balance_history, bank_transaction
import logging
import time
import arrow
import datetime
from sqlalchemy import MetaData, Table
from sqlalchemy.sql import text


def get_sql_data(query, conn):
    """Getting date from SQL server
    args:
    inputs:
           query (str): the query to SQL server
    output:
           df (pd.DataFrame): table in pandas dataframe format
    """

    df = pd.read_sql(query, con=conn)
    return df


def get_df(db_name, sql):
    with ah_db.open_db_connection(db_name) as connection:
        return pd.read_sql(sql, con=connection)


def endpoint():
    return ah_config.get('endpoint.python.url')


def risk_base():
    return ah_config.get('endpoint.python.risk_base')


sqlalchemy_metadata_map = {}


def _get_metadata(db_name):
    if db_name not in sqlalchemy_metadata_map:
        sqlalchemy_metadata_map[db_name] = MetaData()
    return sqlalchemy_metadata_map[db_name]
