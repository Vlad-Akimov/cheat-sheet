import sqlite3
from config import config
from typing import List, Dict, Optional

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(config.DB_NAME)
        self.cursor = self.conn.cursor()
        self._init_db()
        self._migrate_db()  # Добавляем миграции
    
    def rollback(self):
        """Откатывает текущую транзакцию"""
        self.conn.rollback()
        print("Транзакция откачена")
    
    def _init_db(self):
        # Пользователи (обновленная структура)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0
        )
        """)
        
        # Предметы
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)
        
        # Шпаргалки
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS cheatsheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            semester INTEGER,
            type TEXT,
            name TEXT,
            file_id TEXT,
            file_type TEXT,
            price REAL,
            author_id INTEGER,
            is_approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
        """)
        
        # Покупки
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cheatsheet_id INTEGER,
            amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (cheatsheet_id) REFERENCES cheatsheets(id)
        )
        """)
        
        # Таблица запросов на пополнение баланса
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS balance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            proof_text TEXT,
            file_id TEXT,
            file_type TEXT,
            status TEXT DEFAULT 'pending',
            admin_id INTEGER,
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
        """)
            
        self.conn.commit()
    
    def close(self):
        """Закрывает соединение с базой данных"""
        try:
            if self.conn:
                self.conn.close()
                print("Соединение с базой данных закрыто")
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")
    
    def _migrate_db(self):
        """Добавляем отсутствующие колонки в существующие таблицы"""
        try:
            # Проверяем наличие новых колонок в таблице cheatsheets
            self.cursor.execute("PRAGMA table_info(cheatsheets)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            # Добавляем новые колонки, если их нет
            if 'created_at' not in columns:
                self.cursor.execute("ALTER TABLE cheatsheets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if 'approved_at' not in columns:
                self.cursor.execute("ALTER TABLE cheatsheets ADD COLUMN approved_at TIMESTAMP")
            
            self.conn.commit()
            print("Миграции базы данных успешно применены")
                
        except Exception as e:
            print(f"Ошибка при миграции базы данных: {e}")
    
    # Пользователи (обновленный метод)
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавляет или обновляет пользователя с дополнительной информацией"""
        try:
            username = username or f"user_{user_id}"  # Если username None
            full_name = " ".join(filter(None, [first_name, last_name])).strip()
            full_name = full_name if full_name else None
            
            self.cursor.execute(
                """INSERT OR REPLACE INTO users 
                (id, username, first_name, last_name, full_name) 
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, first_name, last_name, full_name)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return False
    
    def get_user_balance(self, user_id: int) -> float:
        self.cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0.0
    
    def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Обновляет баланс пользователя с проверками"""
        try:
            # Проверяем существование пользователя
            self.cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
            if not self.cursor.fetchone():
                self.add_user(user_id, f"user_{user_id}")

            # Обновляем баланс
            self.cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, user_id)
            )
            self.conn.commit()
            
            # Проверяем, что баланс изменился
            new_balance = self.get_user_balance(user_id)
            print(f"Баланс пользователя {user_id} изменен на {amount}. Новый баланс: {new_balance}")
            return True
        except Exception as e:
            print(f"Ошибка при обновлении баланса: {e}")
            self.conn.rollback()
            return False
    
    # Предметы
    def add_subject(self, name: str):
        try:
            self.cursor.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_subjects(self) -> List[str]:
        self.cursor.execute("SELECT name FROM subjects")
        return [row[0] for row in self.cursor.fetchall()]
    
    # Шпаргалки
    def add_cheatsheet(self, subject_id: int, semester: int, type_: str, name: str, file_id: str, file_type: str, price: float, author_id: int) -> int:
        self.cursor.execute(
            "INSERT INTO cheatsheets (subject_id, semester, type, name, file_id, file_type, price, author_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (subject_id, semester, type_, name, file_id, file_type, price, author_id)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_cheatsheet(self, cheatsheet_id: int, user_id: int = None) -> Optional[Dict]:
        """Получает полную информацию о шпаргалке с проверкой прав доступа"""
        self.cursor.execute("""
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, 
            c.file_id, c.file_type, c.price, c.author_id,
            COALESCE(u.username, 'Неизвестный автор') as author,
            datetime(c.created_at, 'localtime') as created_at,
            datetime(c.approved_at, 'localtime') as approved_at
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.id = ? AND (c.is_approved = 1 OR c.author_id = ?)
        """, (cheatsheet_id, user_id if user_id else 0))
        
        result = self.cursor.fetchone()
        if not result:
            return None
        
        return {
            "id": result[0],
            "subject": result[1],
            "semester": result[2],
            "type": result[3],
            "name": result[4],
            "file_id": result[5],
            "file_type": result[6],
            "price": result[7],
            "author_id": result[8],
            "author": result[9],
            "created_at": result[10],
            "approved_at": result[11]
        }
    
    def get_cheatsheets(self, subject: str = None, semester: int = None, type_: str = None, user_id: int = None) -> List[Dict]:
        query = """
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, c.file_id, c.file_type, c.price, 
            COALESCE(u.username, 'Неизвестный автор') as author, c.author_id,
            datetime(c.created_at, 'localtime') as created_at,
            datetime(c.approved_at, 'localtime') as approved_at
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN users u ON c.author_id = u.id
        WHERE (c.is_approved = 1 OR c.author_id = ?)
        """
        
        params = [user_id if user_id else 0]
        
        if subject is not None:
            query += " AND s.name = ?"
            params.append(subject)
        if semester is not None:
            query += " AND c.semester = ?"
            params.append(semester)
        if type_ is not None:
            query += " AND c.type = ?"
            params.append(type_)
        
        query += " ORDER BY c.approved_at DESC"
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        return [{
            "id": row[0],
            "subject": row[1],
            "semester": row[2],
            "type": row[3],
            "name": row[4],
            "file_id": row[5],
            "file_type": row[6],
            "price": row[7],
            "author": row[8],
            "author_id": row[9],
            "created_at": row[10],
            "approved_at": row[11]
        } for row in results]
    
    def get_user_cheatsheets(self, user_id: int, subject: str = None, semester: int = None, type_: str = None) -> List[Dict]:
        """Получает шпаргалки пользователя с возможностью фильтрации"""
        # Получаем шпаргалки, созданные пользователем
        query = """
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, c.price, c.is_approved 
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        WHERE c.author_id = ?
        """
        
        params = [user_id]
        
        # Добавляем фильтры
        if subject:
            query += " AND s.name = ?"
            params.append(subject)
        if semester:
            query += " AND c.semester = ?"
            params.append(semester)
        if type_:
            query += " AND c.type = ?"
            params.append(type_)
        
        self.cursor.execute(query, params)
        created = [{
            "id": row[0],
            "subject": row[1],
            "semester": row[2],
            "type": row[3],
            "name": row[4],
            "price": row[5],
            "is_approved": bool(row[6]),
            "is_purchased": False
        } for row in self.cursor.fetchall()]
        
        # Получаем шпаргалки, купленные пользователем
        query = """
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, c.price 
        FROM purchases p
        JOIN cheatsheets c ON p.cheatsheet_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        WHERE p.user_id = ?
        """
        
        params = [user_id]
        
        if subject:
            query += " AND s.name = ?"
            params.append(subject)
        if semester:
            query += " AND c.semester = ?"
            params.append(semester)
        if type_:
            query += " AND c.type = ?"
            params.append(type_)
        
        self.cursor.execute(query, params)
        purchased = [{
            "id": row[0],
            "subject": row[1],
            "semester": row[2],
            "type": row[3],
            "name": row[4],
            "price": row[5],
            "is_approved": True,
            "is_purchased": True
        } for row in self.cursor.fetchall()]
        
        return created + purchased
    
    def approve_cheatsheet(self, cheatsheet_id: int):
        """Одобряет шпаргалку"""
        try:
            self.cursor.execute(
                "UPDATE cheatsheets SET is_approved = 1, approved_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (cheatsheet_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при одобрении шпаргалки: {e}")
            return False
    
    def reject_cheatsheet(self, cheatsheet_id: int):
        self.cursor.execute("DELETE FROM cheatsheets WHERE id = ?", (cheatsheet_id,))
        self.conn.commit()
    
    # Покупки
    def add_purchase(self, user_id: int, cheatsheet_id: int, amount: float) -> bool:
        """Добавляет запись о покупке и возвращает статус операции"""
        try:
            self.cursor.execute(
                "INSERT INTO purchases (user_id, cheatsheet_id, amount) VALUES (?, ?, ?)",
                (user_id, cheatsheet_id, amount)
            )
            self.conn.commit()
            print(f"Запись о покупке добавлена: user={user_id}, item={cheatsheet_id}, amount={amount}")
            return True
        except Exception as e:
            print(f"Ошибка при добавлении покупки: {e}")
            self.conn.rollback()
            return False
    
    def add_balance_request(self, user_id: int, amount: float, proof_text: str = None, 
                          file_id: str = None, file_type: str = None) -> int:
        """Добавляет запрос на пополнение с проверкой"""
        try:
            self.cursor.execute(
                """INSERT INTO balance_requests 
                (user_id, amount, proof_text, file_id, file_type) 
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, amount, proof_text, file_id, file_type)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Ошибка добавления запроса: {e}")
            return None

    def get_pending_requests(self) -> List[Dict]:
        """Получает все ожидающие запросы"""
        self.cursor.execute("""
        SELECT br.*, u.username 
        FROM balance_requests br
        JOIN users u ON br.user_id = u.id
        WHERE br.status = 'pending'
        ORDER BY br.created_at
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    def update_request_status(self, request_id: int, status: str, admin_id: int) -> bool:
        """Обновляет статус запроса на пополнение баланса"""
        try:
            self.cursor.execute(
                """UPDATE balance_requests 
                SET status = ?, admin_id = ?, processed_at = CURRENT_TIMESTAMP 
                WHERE id = ?""",
                (status, admin_id, request_id)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка обновления статуса запроса: {e}")
            self.conn.rollback()
            return False
    
    def get_purchased_cheatsheets(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""
        SELECT c.id, s.name, c.semester, c.type, c.name, c.price 
        FROM purchases p
        JOIN cheatsheets c ON p.cheatsheet_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        WHERE p.user_id = ?
        """, (user_id,))
        return [{
            "id": row[0],
            "subject": row[1],
            "semester": row[2],
            "type": row[3],
            "name": row[4],
            "price": row[5],
            "is_approved": True,
            "is_purchased": True
        } for row in self.cursor.fetchall()]

db = Database()