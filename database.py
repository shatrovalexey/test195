import json
import asyncpg
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import os

class DatabaseConfig:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.conn_params = self._build_conn_params()
    
    def _load_config(self) -> Dict[str, Any]:
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
    
    def _build_conn_params(self) -> Dict[str, Any]:
        db_config = self.config.get("database", {})
        return {
            'host': os.getenv('DB_HOST', db_config.get('host', 'localhost')),
            'port': os.getenv('DB_PORT', db_config.get('port', 5432)),
            'database': os.getenv('DB_NAME', db_config.get('database', 'postgres')),
            'user': os.getenv('DB_USER', db_config.get('user', 'postgres')),
            'password': os.getenv('DB_PASSWORD', db_config.get('password', 'password'))
        }
    
    def get_param(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

class Database:
    def __init__(self, config_path: str = "config.json"):
        self.config = DatabaseConfig(config_path)
        self.pool = None
    
    async def init_pool(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(**self.config.conn_params, min_size=1, max_size=10)
        return self.pool
    
    async def close_pool(self):
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def get_connection(self):
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        async with self.get_connection() as conn:
            if fetch_one:
                result = await conn.fetchrow(query, *params) if params else await conn.fetchrow(query)
                return dict(result) if result else None
            elif fetch_all:
                results = await conn.fetch(query, *params) if params else await conn.fetch(query)
                return [dict(r) for r in results]
            else:
                result = await conn.execute(query, *params) if params else await conn.execute(query)
                return {"affected_rows": result.split()[-1] if result else 0}

db = Database()