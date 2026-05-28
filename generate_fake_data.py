#!/usr/bin/env python

import asyncio
import random
import hashlib
import json
from datetime import datetime, timedelta
from faker import Faker
from database import db
from utils.security import hash_password

fake_ru = Faker('ru_RU')
fake_en = Faker('en_US')

def generate_sha1(data: str) -> str:
    return hashlib.sha1(data.encode()).hexdigest()

async def check_and_create_tables():
    """Проверка и создание таблиц с правильной структурой"""
    print("\n📋 Проверка структуры таблиц...")
    
    async with db.get_connection() as conn:
        # Проверяем существование колонок в таблице users
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        existing_columns = [col['column_name'] for col in columns]
        
        # Добавляем недостающие колонки
        if 'is_admin' not in existing_columns:
            await conn.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
            print("  ✓ Добавлена колонка is_admin")
        
        if 'is_blocked' not in existing_columns:
            await conn.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
            print("  ✓ Добавлена колонка is_blocked")
        
        print("✅ Структура таблиц проверена")

async def generate_fake_users(count: int = 50):
    """Генерация фейковых пользователей"""
    print(f"\n📝 Генерация {count} пользователей...")
    
    users = []
    emails = set()
    
    async with db.get_connection() as conn:
        for i in range(count):
            while True:
                email = fake_en.email()
                if email not in emails:
                    emails.add(email)
                    break
            
            is_admin = random.choice([True] + [False] * 9)
            is_blocked = random.choice([True] + [False] * 19)
            
            try:
                result = await conn.fetchrow("""
                    INSERT INTO users (full_name, email, password_hash, is_admin, is_blocked)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, full_name, email, is_admin, is_blocked
                """, fake_ru.name(), email, hash_password('password123'), is_admin, is_blocked)
                
                if result:
                    user = dict(result)
                    users.append(user)
                    print(f"  ✓ Создан пользователь: {user['full_name'][:30]} - ID: {user['id']}")
            except Exception as e:
                print(f"  ✗ Ошибка: {e}")
    
    print(f"✅ Создано {len(users)} пользователей")
    return users

async def generate_fake_resources(count: int = 100):
    """Генерация фейковых ресурсов"""
    print(f"\n📝 Генерация {count} ресурсов...")
    
    resources = []
    resource_types = ['document', 'image', 'video', 'audio', 'archive']
    
    async with db.get_connection() as conn:
        for i in range(count):
            resource_id = generate_sha1(fake_en.uuid4() + str(datetime.now()))
            resource_type = random.choice(resource_types)
            
            metadata = {
                'name': fake_en.file_name(),
                'type': resource_type,
                'size': random.randint(1024, 10485760),
                'created_by': fake_ru.name(),
                'description': fake_ru.text(max_nb_chars=100)
            }
            
            try:
                await conn.execute("""
                    INSERT INTO resources (id, metadata)
                    VALUES ($1, $2)
                """, resource_id, json.dumps(metadata))
                
                resources.append({'id': resource_id, 'metadata': metadata})
                
                if (i + 1) % 20 == 0:
                    print(f"  ✓ Создано {i + 1} ресурсов...")
                    
            except Exception as e:
                print(f"  ✗ Ошибка: {e}")
    
    print(f"✅ Создано {len(resources)} ресурсов")
    return resources

async def generate_fake_permissions(users, resources):
    """Генерация фейковых прав доступа"""
    print(f"\n📝 Генерация прав доступа...")
    
    if not users or not resources:
        print("  ⚠️ Нет пользователей или ресурсов для создания прав")
        return []
    
    permission_types = ['read', 'write', 'delete', 'manage']
    permissions = []
    
    async with db.get_connection() as conn:
        created_count = 0
        
        # Для каждого ресурса даем права нескольким пользователям
        for resource in resources[:50]:  # Берем первые 50 ресурсов для скорости
            # Выбираем случайных пользователей
            num_users = random.randint(1, min(5, len(users)))
            selected_users = random.sample(users, num_users)
            
            for user in selected_users:
                # Даем случайные права
                num_perms = random.randint(1, 3)
                selected_perms = random.sample(permission_types, num_perms)
                
                for perm_type in selected_perms:
                    try:
                        await conn.execute("""
                            INSERT INTO resource_permissions 
                            (user_id, resource_id, permission_type, granted_by, is_active)
                            VALUES ($1, $2, $3, $4, TRUE)
                            ON CONFLICT (user_id, resource_id, permission_type) 
                            DO NOTHING
                        """, user['id'], resource['id'], perm_type, user['id'])
                        
                        created_count += 1
                        
                    except Exception as e:
                        pass
            
            if created_count % 50 == 0 and created_count > 0:
                print(f"  ✓ Создано {created_count} прав...")
    
    print(f"✅ Создано {created_count} прав доступа")
    return permissions

async def generate_stats():
    """Показ статистики"""
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("="*60)
    
    async with db.get_connection() as conn:
        # Пользователи
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        admins_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        blocked_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_blocked = TRUE")
        
        print(f"\n👥 Пользователи:")
        print(f"   Всего: {users_count}")
        print(f"   Администраторов: {admins_count}")
        print(f"   Заблокированных: {blocked_count}")
        
        # Ресурсы
        resources_count = await conn.fetchval("SELECT COUNT(*) FROM resources")
        print(f"\n📁 Ресурсы:")
        print(f"   Всего: {resources_count}")
        
        # Права доступа
        permissions_count = await conn.fetchval("SELECT COUNT(*) FROM resource_permissions WHERE is_active = TRUE")
        print(f"\n🔑 Активные права доступа:")
        print(f"   Всего: {permissions_count}")
        
        # Типы ресурсов
        types = await conn.fetch("""
            SELECT metadata->>'type' as type, COUNT(*) as count
            FROM resources 
            GROUP BY metadata->>'type'
            ORDER BY count DESC
        """)
        
        if types:
            print(f"\n📊 Типы ресурсов:")
            for t in types[:5]:
                print(f"   {t['type']}: {t['count']}")

async def clear_all_data():
    """Очистка всех данных"""
    print("\n⚠️  ВНИМАНИЕ! Это удалит все данные из таблиц!")
    confirm = input("Вы уверены? (yes/no): ")
    
    if confirm.lower() == 'yes':
        async with db.get_connection() as conn:
            await conn.execute("TRUNCATE TABLE resource_permissions CASCADE")
            await conn.execute("TRUNCATE TABLE resources CASCADE")
            await conn.execute("TRUNCATE TABLE users CASCADE")
        print("✅ Все данные удалены")
        return True
    return False

async def main():
    """Основная функция"""
    print("="*60)
    print("🔧 ГЕНЕРАТОР ФЕЙКОВЫХ ДАННЫХ")
    print("="*60)
    
    # Настройки
    num_users = 30
    num_resources = 50
    
    print(f"\nНастройки:")
    print(f"  - Пользователей: {num_users}")
    print(f"  - Ресурсов: {num_resources}")
    
    # Инициализация БД
    await db.init_pool()
    
    # Очистка данных
    clear = input("\nОчистить существующие данные перед генерацией? (yes/no): ")
    if clear.lower() == 'yes':
        if not await clear_all_data():
            await db.close_pool()
            return
    
    try:
        # Проверка структуры таблиц
        await check_and_create_tables()
        
        print("\n🚀 Начинаем генерацию данных...")
        
        # Генерация данных
        users = await generate_fake_users(num_users)
        
        if not users:
            print("❌ Не удалось создать пользователей")
            return
        
        resources = await generate_fake_resources(num_resources)
        
        if resources:
            await generate_fake_permissions(users, resources)
        
        # Статистика
        await generate_stats()
        
        print("\n" + "="*60)
        print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print("="*60)
        print("\n📝 Тестовые данные:")
        print("   - Пароль для всех пользователей: password123")
        print("   - Админ создается автоматически при запуске main.py")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close_pool()

def run_sync_version():
    """Синхронная версия (проще и надежнее)"""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    print("="*60)
    print("🔧 ГЕНЕРАТОР ФЕЙКОВЫХ ДАННЫХ (СИНХРОННАЯ ВЕРСИЯ)")
    print("="*60)
    
    # Подключение
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='postgres',
        user='postgres',
        password='password',
        cursor_factory=RealDictCursor
    )
    
    try:
        with conn.cursor() as cur:
            # Проверка колонок
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            columns = [row['column_name'] for row in cur.fetchall()]
            
            if 'is_admin' not in columns:
                cur.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
            if 'is_blocked' not in columns:
                cur.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
            conn.commit()
            
            # Очистка
            choice = input("\nОчистить данные? (yes/no): ")
            if choice.lower() == 'yes':
                cur.execute("TRUNCATE TABLE resource_permissions CASCADE")
                cur.execute("TRUNCATE TABLE resources CASCADE")
                cur.execute("TRUNCATE TABLE users CASCADE")
                conn.commit()
                print("✅ Данные очищены")
            
            # Генерация пользователей
            print("\n📝 Генерация пользователей...")
            users = []
            for _ in range(30):
                cur.execute("""
                    INSERT INTO users (full_name, email, password_hash, is_admin, is_blocked)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    fake_ru.name(),
                    fake_en.email(),
                    hashlib.sha1(b'password123').hexdigest(),
                    random.choice([True, False, False, False]),
                    random.choice([True, False, False, False, False])
                ))
                user_id = cur.fetchone()['id']
                users.append({'id': user_id})
                conn.commit()
            
            print(f"✅ Создано {len(users)} пользователей")
            
            # Генерация ресурсов
            print("\n📝 Генерация ресурсов...")
            resources = []
            for _ in range(50):
                resource_id = hashlib.sha1(fake_en.uuid4().encode()).hexdigest()
                metadata = {
                    'name': fake_en.file_name(),
                    'type': random.choice(['doc', 'img', 'video']),
                    'size': random.randint(1000, 1000000)
                }
                cur.execute("""
                    INSERT INTO resources (id, metadata)
                    VALUES (%s, %s)
                    RETURNING id
                """, (resource_id, json.dumps(metadata)))
                resources.append({'id': resource_id})
                conn.commit()
            
            print(f"✅ Создано {len(resources)} ресурсов")
            
            # Генерация прав
            print("\n📝 Генерация прав доступа...")
            count = 0
            for user in users[:20]:
                for resource in random.sample(resources, min(10, len(resources))):
                    perm_type = random.choice(['read', 'write', 'delete'])
                    try:
                        cur.execute("""
                            INSERT INTO resource_permissions (user_id, resource_id, permission_type, granted_by)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (user['id'], resource['id'], perm_type, user['id']))
                        count += 1
                        conn.commit()
                    except:
                        pass
            
            print(f"✅ Создано {count} прав")
            
            # Статистика
            cur.execute("SELECT COUNT(*) as count FROM users")
            print(f"\n📊 Итого: {cur.fetchone()['count']} пользователей")
            
            cur.execute("SELECT COUNT(*) as count FROM resources")
            print(f"   {cur.fetchone()['count']} ресурсов")
            
    finally:
        conn.close()

if __name__ == "__main__":
    # Выберите версию
    print("Выберите версию:")
    print("1. Асинхронная (требует asyncpg)")
    print("2. Синхронная (рекомендуется)")
    
    choice = input("Ваш выбор (1/2): ")
    
    if choice == '1':
        asyncio.run(main())
    else:
        run_sync_version()