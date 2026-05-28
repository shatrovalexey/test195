import json
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os

class DatabaseConfig:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.conn_params = self._build_conn_params()
    
    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "postgres",
                    "user": "postgres",
                    "password": "password"
                }
            }
    
    def _build_conn_params(self) -> dict:
        db_config = self.config.get("database", {})
        return {
            'host': os.getenv('DB_HOST', db_config.get('host', 'localhost')),
            'port': os.getenv('DB_PORT', db_config.get('port', 5432)),
            'database': os.getenv('DB_NAME', db_config.get('database', 'postgres')),
            'user': os.getenv('DB_USER', db_config.get('user', 'postgres')),
            'password': os.getenv('DB_PASSWORD', db_config.get('password', 'password'))
        }

class Database:
    def __init__(self, config_path: str = "config.json"):
        self.config = DatabaseConfig(config_path)
    
    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(**self.config.conn_params, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch_one:
                    result = cur.fetchone()
                    return dict(result) if result else None
                elif fetch_all:
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                else:
                    return {"affected_rows": cur.rowcount}

# Глобальный экземпляр
db = Database()