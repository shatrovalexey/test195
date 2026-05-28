from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import db
from query_loader import query_loader
from utils.security import init_jwt_config, hash_password

async def init_database():
    """Асинхронная инициализация базы данных"""
    try:
        # Создание таблиц
        async with db.get_connection() as conn:
            # Создание таблицы пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash CHAR(40) NOT NULL,
                    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
                    is_blocked BOOLEAN DEFAULT FALSE NOT NULL
                )
            """)
            
            # Создание таблицы ресурсов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id CHAR(40) PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    metadata JSONB
                )
            """)
            
            # Создание таблицы прав доступа
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_permissions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    resource_id CHAR(40) NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
                    permission_type VARCHAR(50) NOT NULL,
                    granted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    UNIQUE(user_id, resource_id, permission_type)
                )
            """)
            
            # Создание администратора по умолчанию
            admin_password = hash_password("admin123")
            
            # Проверка существования админа
            result = await conn.fetchval("SELECT id FROM users WHERE email = 'admin@example.com'")
            if not result:
                await conn.execute("""
                    INSERT INTO users (full_name, email, password_hash, is_admin)
                    VALUES ($1, $2, $3, TRUE)
                """, "Admin", "admin@example.com", admin_password)
            
            print("✓ Database initialized successfully")
            print("✓ Default admin: admin@example.com / admin123")
            
    except Exception as e:
        print(f"Database initialization warning: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация JWT
    secret_key = "your-secret-key-change-in-production-12345"
    init_jwt_config(
        secret_key=secret_key,
        algorithm="HS256",
        access_expire_minutes=30,
        refresh_expire_days=7
    )
    
    # Инициализация пула соединений
    await db.init_pool()
    
    # Инициализация БД
    await init_database()
    
    print("✓ Application started")
    yield
    
    # Закрытие пула соединений
    await db.close_pool()
    print("Shutting down...")

app = FastAPI(
    title="Resource Management API",
    description="API with JWT authentication",
    version="2.0.0",
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
from routers import auth, users, resources
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resources.router)

@app.get("/")
async def root():
    return {
        "message": "Resource Management API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )