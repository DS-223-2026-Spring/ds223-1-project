from loguru import logger
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


class SQLHandler:
    """
    PostgreSQL database handler using psycopg2 + pandas.

    Responsibilities:
        - Manage DB connection lifecycle
        - Execute SELECT queries safely (read-only guard)
        - Perform bulk inserts via execute_values
        - Provide schema/table context helpers

    Non-responsibilities:
        - Business logic
        - Schema validation
        - Query building safety beyond basic SELECT restriction
    """
    def __init__(self, host, dbname, user, password, port=5432, schema="public"):
        """
        Initialize database connection.

        Args:
            host (str): DB host
            dbname (str): database name
            user (str): username
            password (str): password
            port (int): DB port
            schema (str): default schema (default = public)
        """
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
        """
        Set active schema for future operations.
        """
        self.schema = schema_name
        logger.info(f"Using schema: {self.schema}")

    def set_table(self, table_name: str):
        """
        Set active table reference.

        This builds:
            self.table_ref = schema.table
        """
        self.table_name = table_name
        self.table_ref = f"{self.schema}.{self.table_name}"
        logger.info(f"Using table: {self.table_ref}")

    def commit(self):
        """
        Commit current transaction.
        """
        self.conn.commit()
        logger.info("Transaction committed")

    def rollback(self):
        """
        Roll back current transaction.
        """
        self.conn.rollback()
        logger.info("Transaction rolled back")

    def close(self):
        """
        Close DB connection and cursor.
        """
        self.cursor.close()
        self.conn.close()
        logger.info("Connection closed")

    def get_columns(self):
        """
        Get column names for current schema.table.

        Returns:
            list[str]
        """
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """
        self.cursor.execute(query, (self.schema, self.table_name))
        return [column[0] for column in self.cursor.fetchall()]

    def delete_rows(self, condition: str):
        """
        Delete rows using raw SQL condition.

        Example:
            delete_rows("customer_id = 5")
        """
        query = f"DELETE FROM {self.table_ref} WHERE {condition}"
        self.cursor.execute(query)
        logger.info(query)

    def from_sql(self, query: str, parse_dates=None, dtypes=None) -> pd.DataFrame:
        """
        Execute arbitrary SQL and return DataFrame.
        """
        df = pd.read_sql_query(query, self.conn, parse_dates=parse_dates, dtype=dtypes)
        logger.info(f"Fetched shape: {df.shape}")
        return df

    def select(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Execute SELECT query safely.

        Safety:
            - Only allows queries starting with SELECT
            - Prevents accidental writes

        Args:
            query: SQL SELECT query
            params: query parameters

        Returns:
            pandas.DataFrame
        """
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
        """
        Bulk insert a pandas DataFrame into a table.

        Args:
            df: DataFrame to insert
            table: target table name (without schema)

        Behavior:
            - NaN → None conversion
            - column names forced to lowercase
            - uses execute_values for performance

        Assumptions:
            - table exists in schema
            - dataframe columns match DB schema
        """
        if df.empty:
            logger.warning("Empty DataFrame. Nothing to insert.")
            return

        full_table = f"{self.schema}.{table}"
        df = df.copy().replace({np.nan: None})
        df.columns = [column.lower() for column in df.columns]

        columns = list(df.columns)
        cols_sql = ", ".join(columns)
        values = [tuple(row) for row in df.to_numpy()]

        query = f"""
            INSERT INTO {full_table} ({cols_sql})
            VALUES %s
        """

        try:
            execute_values(self.cursor, query, values)
            self.conn.commit()
            logger.info(
                f"Inserted {len(values)} rows into {full_table} | cols={len(columns)}"
            )
        except Exception as exc:
            self.conn.rollback()
            logger.error(f"INSERT DF failed: {exc}")
            raise
