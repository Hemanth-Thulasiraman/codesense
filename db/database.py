import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable not set")

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    1,
    10,
    DATABASE_URL
)

def get_connection():
    """Borrow a connection from the pool."""
    try:
        return connection_pool.getconn()
    except psycopg2.pool.PoolError as e:
        raise RuntimeError("No database connections available. Pool exhausted.") from e
        
def release_connection(conn):
    """Return a connection to the pool."""
    connection_pool.putconn(conn)

def initialize_schema():
    """Run schema.sql to create tables if they don't exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        with open("db/schema.sql", "r") as file:
            sql = file.read()
        cursor.execute(sql)
        conn.commit()
        print("Schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Schema initialization failed: {e}")
        raise
    finally:
        release_connection(conn)