import sqlite3
from config import TOKEN
import uuid

# Функция для инициализации базы данных
def init_db():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Таблица для хранения клиентов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            object TEXT NOT NULL,
            insect_quantity TEXT NOT NULL,
            disinsect_experience TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL
        )
    ''')

    # Таблица для хранения заявок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            disinsector_id INTEGER,
            order_id TEXT NOT NULL,
            order_status TEXT DEFAULT 'Новая',
            order_date TEXT,
            estimated_price REAL,
            final_price REAL,
            poison_type TEXT,
            insect_type TEXT,
            insect_quantity TEXT,
            client_contact TEXT,
            client_address TEXT,
            client_property_type TEXT,
            client_area REAL,
            FOREIGN KEY (client_id) REFERENCES users(id)
        )
    ''')

    # Таблица для хранения данных дезинсекторов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS disinsectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            user_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()


# Функция для добавления нового клиента в базу данных
def add_client(name, object_type, insect_quantity, disinsect_experience, phone, address):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (name, object, insect_quantity, disinsect_experience, phone, address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, object_type, insect_quantity, disinsect_experience, phone, address))
    conn.commit()
    client_id = cur.lastrowid
    conn.close()
    return client_id


# Функция для создания новой заявки
def create_order(client_id, order_id, disinsector_id=None, estimated_price=None, final_price=None, poison_type=None,
                 insect_type=None, client_area=None):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO orders (client_id, order_id, disinsector_id, estimated_price, final_price, poison_type, insect_type, client_area)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, order_id, disinsector_id, estimated_price, final_price, poison_type, insect_type, client_area))
    conn.commit()
    conn.close()

# Функция для получения дезинсектора по токену
def get_disinsector_by_token(token):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM disinsectors WHERE token = ?', (token,))
    disinsector = cur.fetchone()
    conn.close()
    return disinsector

# Функция для получения всех токенов дезинсекторов
def get_all_disinsector_tokens():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('SELECT token FROM disinsectors')
    tokens = [row[0] for row in cur.fetchall()]
    conn.close()
    return tokens

# Функция для обновления заявки
def update_order(order_id, poison_type=None, insect_type=None, client_area=None, estimated_price=None, final_price=None,
                 order_status=None):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    cur.execute('''
        UPDATE orders
        SET poison_type = ?, insect_type = ?, client_area = ?, estimated_price = ?, final_price = ?, order_status = ?
        WHERE order_id = ?
    ''', (poison_type, insect_type, client_area, estimated_price, final_price, order_status, order_id))

    conn.commit()
    conn.close()

# Инициализация базы данных при первом запуске
init_db()
