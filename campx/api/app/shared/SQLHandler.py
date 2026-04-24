"""Backend-local copy of the shared SQL helper used by ETL and backend."""

from __future__ import annotations

from loguru import logger
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


class SQLHandler:
    def __init__(self, host, dbname, user, password, port=5432, schema="public"):
        self.schema = schema
        self.table_name = None

        self.conn = psycopg2.connect(
            host=host,
            dbname=dbname,
            user=user,
            password=password,
            port=port,
        )
        self.cursor = self.conn.cursor()

        logger.info(f"Connected to PostgreSQL: {dbname}@{host}:{port}")

    def set_schema(self, schema_name: str):
        self.schema = schema_name
        logger.info(f"Using schema: {self.schema}")

    def set_table(self, table_name: str):
        self.table_name = table_name
        self.table_ref = f"{self.schema}.{self.table_name}"
        logger.info(f"Using table: {self.table_ref}")

    def commit(self):
        self.conn.commit()
        logger.info("Transaction committed")

    def close(self):
        self.cursor.close()
        self.conn.close()
        logger.info("Connection closed")

    def get_columns(self):
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """
        self.cursor.execute(query, (self.schema, self.table_name))
        return [c[0] for c in self.cursor.fetchall()]

    def delete_rows(self, condition: str):
        query = f"DELETE FROM {self.table_ref} WHERE {condition}"
        self.cursor.execute(query)
        logger.info(query)

    def from_sql(self, query: str, parse_dates=None, dtypes=None) -> pd.DataFrame:
        df = pd.read_sql_query(query, self.conn, parse_dates=parse_dates, dtype=dtypes)
        logger.info(f"Fetched shape: {df.shape}")
        return df

    def select(self, query: str, params: tuple = None) -> pd.DataFrame:
        if not query.strip().lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed")

        logger.info("Executing SELECT query")

        try:
            df = pd.read_sql_query(query, self.conn, params=params)
            logger.info(f"SELECT completed | shape={df.shape}")
            return df
        except Exception as exc:
            logger.error(f"SELECT failed: {exc}")
            raise

    def insert_dataframe(self, df: pd.DataFrame, table: str):
        if df.empty:
            logger.warning("Empty DataFrame. Nothing to insert.")
            return

        full_table = f"{self.schema}.{table}"
        df = df.copy()
        df = df.replace({np.nan: None})
        df.columns = [c.lower() for c in df.columns]

        columns = list(df.columns)
        cols_sql = ", ".join(columns)
        values = [tuple(x) for x in df.to_numpy()]

        query = f"""
            INSERT INTO {full_table} ({cols_sql})
            VALUES %s
        """

        try:
            execute_values(self.cursor, query, values)
            self.conn.commit()
            logger.info(f"Inserted {len(values)} rows into {full_table} | cols={len(columns)}")
        except Exception as exc:
            self.conn.rollback()
            logger.error(f"INSERT DF failed: {exc}")
            raise

