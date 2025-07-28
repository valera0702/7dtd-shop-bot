import sqlite3
import threading # <--- ДОБАВЬТЕ ЭТОТ ИМПОРТ В НАЧАЛЕ ФАЙЛА
from contextlib import contextmanager

class Database:
    def __init__(self, db_name='shop.db'):
        # Сохраняем имя файла БД
        self.db_name = db_name
        # Создаем потокобезопасное хранилище
        self.local = threading.local()
        # Вызываем инициализацию БД
        self.init_db()

    def get_connection(self):
        # Проверяем, есть ли подключение в текущем потоке
        if not hasattr(self.local, "conn") or self.local.conn is None:
            # Если нет, создаем новое
            self.local.conn = sqlite3.connect(self.db_name)
            # Эта строка позволяет обращаться к колонкам по имени (cat['name'])
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn

    @contextmanager
    def get_cursor(self):
        # Получаем соединение для текущего потока
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            cursor.close()

    def close_connection(self):
        if hasattr(self.local, "conn") and self.local.conn is not None:
            self.local.conn.close()
            self.local.conn = None

    def init_db(self):
        with self.get_cursor() as cur:
            # Создаем таблицу состояний FSM
            cur.execute("""
            CREATE TABLE IF NOT EXISTS fsm_data (
                user_id INTEGER PRIMARY KEY,
                state TEXT,
                data TEXT
            )
            """)

            # Таблица пользователей
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0,
                game_nickname TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Таблица категорий
            cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            )
            """)
            
            # Таблица подкатегорий
            cur.execute("""
            CREATE TABLE IF NOT EXISTS subcategories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL UNIQUE,
                description TEXT,
                category_id INTEGER,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
            """)
            
            # Таблица товаров (обновленная)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,       -- <--- КОЛИЧЕСТВО
                quality INTEGER NOT NULL DEFAULT 1,     -- <--- КАЧЕСТВО
                rcon_command TEXT,
                category_id INTEGER,
                subcategory_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id) REFERENCES categories(id),
                FOREIGN KEY(subcategory_id) REFERENCES subcategories(id)
            )
            """)
            
            # Таблица корзины
            cur.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER REFERENCES users(user_id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, product_id)
            )
            """)
            
            # Таблица рефералов
            cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL REFERENCES users(user_id),
                referred_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Таблица реферальных бонусов
            cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL REFERENCES users(user_id),
                referral_id INTEGER NOT NULL REFERENCES users(user_id),
                amount REAL NOT NULL,
                bonus REAL NOT NULL,
                invoice_id TEXT NOT NULL, 
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Таблица промокодов
            cur.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                promo_type TEXT NOT NULL,
                value REAL NOT NULL,
                expiration_date TIMESTAMP,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Таблица использованных промокодов
            cur.execute("""
            CREATE TABLE IF NOT EXISTS used_promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                promocode_id INTEGER NOT NULL REFERENCES promocodes(id),
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Создаем категорию по умолчанию, если ее нет
            cur.execute("SELECT * FROM categories WHERE name = 'Без категории'")
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO categories (name, description)
                VALUES ('Без категории', 'Товары без категории')
                """)
    
    # Методы для работы с пользователями
    def add_user(self, user_id):
        with self.get_cursor() as cur:
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    
    def get_balance(self, user_id):
        with self.get_cursor() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0.0
    
    def update_balance(self, user_id, amount):
        with self.get_cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id = ?
            """, (amount, user_id))
    
    def update_user_nickname(self, user_id: int, nickname: str):
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE users SET game_nickname = ? WHERE user_id = ?",
                (nickname, user_id)
            )
    
    def get_user_nickname(self, user_id: int) -> str:
        with self.get_cursor() as cur:
            cur.execute("SELECT game_nickname FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            return result[0] if result else None
    
    # Методы для работы с товарами
    def add_product(self, name, description, price, count, quality, rcon_command, category_id, subcategory_id=None):
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO products (name, description, price, count, quality, rcon_command, category_id, subcategory_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, description, price, count, quality, rcon_command, category_id, subcategory_id))
    
    def get_product(self, product_id):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            return cur.fetchone()
    
    def get_all_products(self):
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT p.id, p.name, p.description, p.price, 
                       c.name as category_name, s.name as subcategory_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
            """)
            return cur.fetchall()
    
    def update_product(self, product_id: int, name: str, description: str, price: float, 
                      command_template: str, category_id: int = None, subcategory_id: int = None):
        """Обновление существующего товара"""
        with self.get_cursor() as cur:
            cur.execute("""
                UPDATE products
                SET name = ?, description = ?, price = ?, command_template = ?,
                    category_id = ?, subcategory_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, description, price, command_template, category_id, subcategory_id, product_id))
    
    def delete_product(self, product_id: int):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    
    # Методы для работы с категориями
    def add_category(self, name: str, description: str = ""):
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description)
            )
    
    def get_all_categories(self):
        with self.get_cursor() as cur:
            cur.execute("SELECT id, name, description FROM categories")
            return cur.fetchall()
    
    def get_category(self, category_id: int):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            return cur.fetchone()
    
    def get_category_by_name(self, name: str):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM categories WHERE name = ?", (name,))
            return cur.fetchone()
    
    def delete_category(self, category_id: int):
        """Удаление категории с перемещением товаров в категорию по умолчанию"""
        default_cat_id = self.get_default_category_id()
        with self.get_cursor() as cur:
            # Перемещаем товары в категорию по умолчанию
            cur.execute("""
                UPDATE products 
                SET category_id = ?
                WHERE category_id = ?
            """, (default_cat_id, category_id))
            
            # Удаляем саму категорию
            cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    
    def get_default_category_id(self) -> int:
        with self.get_cursor() as cur:
            cur.execute("SELECT id FROM categories WHERE name = 'Без категории'")
            result = cur.fetchone()
            return result[0] if result else 1
    
    # Методы для работы с подкатегориями
    def add_subcategory(self, name: str, category_id: int, description: str = ""):
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO subcategories (name, category_id, description) VALUES (?, ?, ?)",
                (name, category_id, description)
            )
    
    def get_subcategories(self, category_id):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM subcategories WHERE category_id = ?", (category_id,))
            return cur.fetchall()
    
    def get_subcategory(self, subcategory_id: int):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM subcategories WHERE id = ?", (subcategory_id,))
            return cur.fetchone()
    
    def move_products_to_category(self, subcategory_id: int, category_id: int):
        """Перемещает товары из подкатегории в указанную категорию"""
        with self.get_cursor() as cur:
            cur.execute("""
                UPDATE products 
                SET subcategory_id = NULL, 
                    category_id = ?
                WHERE subcategory_id = ?
            """, (category_id, subcategory_id))

    def delete_subcategory(self, subcategory_id: int):
        """Удаление подкатегории по ID"""
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))
    
    # Методы для получения товаров
    def get_products_by_category(self, category_id: int):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE category_id = ? AND subcategory_id IS NULL", (category_id,))
            return cur.fetchall()

# database.py -> class Database

    def get_subcategory_info(self, subcategory_id: int):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM subcategories WHERE id = ?", (subcategory_id,))
            return cur.fetchone()

    def get_category_name(self, category_id: int):
        with self.get_cursor() as cur:
            cur.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
            result = cur.fetchone()
            return result['name'] if result else None
    
    def get_products_without_category(self):
        """Товары без категории"""
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT p.id, p.name, p.description, p.price 
            FROM products p
            WHERE p.category_id IS NULL
            """)
            return cur.fetchall()
    
    def get_products_without_subcategory(self, category_id: int):
        """Товары в категории, но без подкатегории"""
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT p.id, p.name, p.description, p.price 
            FROM products p
            WHERE p.category_id = ? AND p.subcategory_id IS NULL
            """, (category_id,))
            return cur.fetchall()
    
    # Методы для работы с корзиной
    def add_to_cart(self, user_id: int, product_id: int):
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO cart (user_id, product_id, quantity)
                VALUES (?, ?, COALESCE(
                    (SELECT quantity + 1 FROM cart WHERE user_id = ? AND product_id = ?),
                    1
                ))
            """, (user_id, product_id, user_id, product_id))
    
    def get_cart_items(self, user_id):
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT cart.product_id, products.name, products.price, cart.quantity 
                FROM cart 
                JOIN products ON cart.product_id = products.id 
                WHERE cart.user_id = ?
            """, (user_id,))
            return cur.fetchall()
    
    def clear_cart(self, user_id):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    
    # Реферальные методы
    def add_referral(self, referrer_id: int, referred_id: int):
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                (referrer_id, referred_id)
            )
    
    def get_referrer(self, user_id: int) -> int | None:
        with self.get_cursor() as cur:
            cur.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (user_id,))
            result = cur.fetchone()
            return result[0] if result else None
    
    def get_referrals_count(self, user_id: int) -> int:
        with self.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
            return cur.fetchone()[0]
    
    def get_referral_bonuses_total(self, user_id: int) -> float:
        with self.get_cursor() as cur:
            cur.execute("SELECT SUM(bonus) FROM referral_bonuses WHERE referrer_id = ?", (user_id,))
            referral_bonuses = cur.fetchone()[0] or 0.0
            
            cur.execute("""
                SELECT COUNT(*) * 50 
                FROM referrals 
                WHERE referrer_id = ?
            """, (user_id,))
            registration_bonuses = cur.fetchone()[0] or 0.0
            
            return referral_bonuses + registration_bonuses
    
    def add_referral_bonus(self, referrer_id: int, referral_id: int, amount: float, bonus: float, invoice_id: str):
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO referral_bonuses (referrer_id, referral_id, amount, bonus, invoice_id) VALUES (?, ?, ?, ?, ?)",
                (referrer_id, referral_id, amount, bonus, invoice_id)
            )
    
    def can_get_referral_bonus(self, referrer_id: int, referral_id: int, invoice_id: str) -> bool:
        if referrer_id == referral_id:
            return False
            
        with self.get_cursor() as cur:
            cur.execute("SELECT 1 FROM referral_bonuses WHERE invoice_id = ?", (invoice_id,))
            if cur.fetchone():
                return False
                
        return True

    def get_referral_percent(self, ref_count: int) -> float:
        return next((
            p for threshold, p in sorted(REF_BONUS_PERCENTS.items(), reverse=True)
            if ref_count >= threshold
        ), 0.10)
    
    # Методы для работы с промокодами
    def add_promocode(self, code: str, promo_type: str, value: float, 
                     expiration_date: str, max_uses: int):
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO promocodes (
                    code, promo_type, value, expiration_date, max_uses
                ) VALUES (?, ?, ?, ?, ?)
            """, (code, promo_type, value, expiration_date, max_uses))
    
    def get_promocode(self, code: str):
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT id, code, promo_type, value, expiration_date, max_uses, used_count
            FROM promocodes WHERE code = ?
            """, (code,))
            return cur.fetchone()
    
    def get_promocodes_list(self):
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT id, code, promo_type, value, expiration_date, max_uses, used_count
            FROM promocodes
            ORDER BY id DESC
            """)
            return cur.fetchall()
    
    def get_promocode_by_id(self, promo_id: int):
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT id, code, promo_type, value, expiration_date, max_uses, used_count
            FROM promocodes WHERE id = ?
            """, (promo_id,))
            return cur.fetchone()
    
    def delete_promocode(self, promo_id: int):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM promocodes WHERE id = ?", (promo_id,))
            cur.execute("DELETE FROM used_promocodes WHERE promocode_id = ?", (promo_id,))
    
    def mark_promocode_used(self, user_id: int, promocode_id: int):
        with self.get_cursor() as cur:
            cur.execute("""
            UPDATE promocodes 
            SET used_count = used_count + 1 
            WHERE id = ?
            """, (promocode_id,))
            
            cur.execute("""
            INSERT INTO used_promocodes (user_id, promocode_id)
            VALUES (?, ?)
            """, (user_id, promocode_id))
    
    def is_promocode_used(self, user_id: int, promocode_id: int):
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT 1 FROM used_promocodes 
            WHERE user_id = ? AND promocode_id = ?
            """, (user_id, promocode_id))
            return cur.fetchone() is not None

    def get_all_categories(self):
        """Получение всех категорий"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM categories")
            return [dict(row) for row in cur.fetchall()]

    def get_category(self, category_id: int):
        """Получение категории по ID"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_subcategories(self, category_id: int):
        """Получение всех подкатегорий для категории"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM subcategories WHERE category_id = ?", (category_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_subcategory(self, subcategory_id: int):
        """Получение подкатегории по ID"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM subcategories WHERE id = ?", (subcategory_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_products_by_category(self, category_id: int):
        """Получение товаров по категории (без подкатегорий)"""
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT * 
            FROM products 
            WHERE category_id = ? AND subcategory_id IS NULL
            """, (category_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_products_by_subcategory(self, subcategory_id: int):
        """Получение товаров по подкатегории"""
        with self.get_cursor() as cur:
            cur.execute("""
            SELECT * 
            FROM products 
            WHERE subcategory_id = ?
            """, (subcategory_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_product(self, product_id):
        """Получение товара по ID"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def add_to_cart(user_id: int, product_id: int):
        """Добавление товара в корзину"""
        with self.get_cursor() as cur:
            # Проверяем, есть ли уже товар в корзине
            cur.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
            existing = cur.fetchone()
            
            if existing:
                new_quantity = existing['quantity'] + 1
                cur.execute("""
                    UPDATE cart 
                    SET quantity = ? 
                    WHERE user_id = ? AND product_id = ?
                """, (new_quantity, user_id, product_id))
            else:
                cur.execute("""
                    INSERT INTO cart (user_id, product_id, quantity)
                    VALUES (?, ?, 1)
                """, (user_id, product_id))
# Создаем экземпляр базы данных для импорта
db = Database()