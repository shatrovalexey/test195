import json
from typing import Dict, Any

class QueryLoader:
    """Загрузчик SQL запросов из JSON"""
    
    def __init__(self, queries_path: str = "db_queries.json"):
        self.queries_path = queries_path
        self.queries = self._load_queries()
    
    def _load_queries(self) -> Dict[str, Any]:
        """Загрузка запросов из JSON файла"""
        try:
            with open(self.queries_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"Queries file not found: {self.queries_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing queries.json: {e}")
    
    def get_query(self, *keys: str) -> str:
        """Получение запроса по ключам"""
        result = self.queries
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                if result is None:
                    raise KeyError(f"Query not found: {'.'.join(keys)}")
            else:
                raise KeyError(f"Invalid path: {'.'.join(keys)}")
        return result
    
    def format_query(self, *keys: str, **kwargs) -> str:
        """Получение и форматирование запроса"""
        query = self.get_query(*keys)
        if kwargs:
            return query.format(**kwargs)
        return query
    
    def reload(self):
        """Перезагрузка запросов"""
        self.queries = self._load_queries()

# Глобальный экземпляр загрузчика запросов
query_loader = QueryLoader()