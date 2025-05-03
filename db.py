import sqlite3
from config import config
from typing import List, Dict, Union, Optional
import os

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
        # Пользователи
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
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
            # Проверяем наличие колонки name в таблице cheatsheets
            self.cursor.execute("PRAGMA table_info(cheatsheets)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'name' not in columns:
                self.cursor.execute("ALTER TABLE cheatsheets ADD COLUMN name TEXT")
                self.conn.commit()
                print("Добавлена колонка 'name' в таблицу cheatsheets")
                
        except Exception as e:
            print(f"Ошибка при миграции базы данных: {e}")
    
    # Пользователи
    def add_user(self, user_id: int, username: str):
        try:
            username = username or f"user_{user_id}"  # Если username None
            self.cursor.execute(
                "INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)",
                (user_id, username)
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
        """Обновляет баланс пользователя в рамках транзакции"""
        try:
            self.cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, user_id)
            )
            # Проверяем, что баланс изменился
            self.cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            new_balance = self.cursor.fetchone()[0]
            print(f"Баланс пользователя {user_id} изменен на {amount}. Новый баланс: {new_balance}")
            return True
        except Exception as e:
            print(f"Ошибка при обновлении баланса: {e}")
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
    
    def get_cheatsheet(self, cheatsheet_id: int) -> Optional[Dict]:
        """Получает полную информацию о шпаргалке"""
        self.cursor.execute("""
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, 
            c.file_id, c.file_type, c.price, c.author_id,
            COALESCE(u.username, 'Неизвестный автор') as author
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.id = ? AND c.is_approved = 1
        """, (cheatsheet_id,))
        
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
            "author_id": result[8],  # Добавляем author_id
            "author": result[9]
        }
    
    def get_cheatsheets(self, subject: str = None, semester: int = None, type_: str = None) -> List[Dict]:
        query = """
        SELECT c.id, s.name as subject, c.semester, c.type, c.name, c.file_id, c.file_type, c.price, 
            COALESCE(u.username, 'Неизвестный автор') as author
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN users u ON c.author_id = u.id
        WHERE c.is_approved = 1
        """
        
        params = []
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
            "author": row[8]
        } for row in results]
    
    def get_user_cheatsheets(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""
        SELECT c.id, s.name, c.semester, c.type, c.name, c.price, c.is_approved 
        FROM cheatsheets c
        JOIN subjects s ON c.subject_id = s.id
        WHERE c.author_id = ?
        """, (user_id,))
        return [{
            "id": row[0],
            "subject": row[1],
            "semester": row[2],
            "type": row[3],
            "name": row[4],
            "price": row[5],
            "is_approved": bool(row[6])
        } for row in self.cursor.fetchall()]
    
    def approve_cheatsheet(self, cheatsheet_id: int):
        """Одобряет шпаргалку"""
        try:
            self.cursor.execute("UPDATE cheatsheets SET is_approved = 1 WHERE id = ?", (cheatsheet_id,))
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

db = Database()