import sqlite3
import logging

def init_db():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Таблица для хранения данных клиентов
    cur.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
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
            order_id TEXT NOT NULL UNIQUE,
            object_type TEXT,
            insect_quantity TEXT,
            disinsect_experience TEXT,
            order_status TEXT DEFAULT 'Новая',
            order_date TEXT,
            estimated_price REAL,
            final_price REAL,
            poison_type TEXT,
            insect_type TEXT,
            client_area REAL,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (disinsector_id) REFERENCES disinsectors(id)
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

    # Таблица для хранения данных администратора
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Функция для добавления администратора в таблицу admin
def add_admin(name, email, password):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Проверка на уникальность email
    cur.execute('SELECT * FROM admins WHERE email = ?', (email,))
    existing_admin = cur.fetchone()

    if existing_admin:
        return "Ошибка: Этот email уже используется."

    try:
        cur.execute('''
            INSERT INTO admins (name, email, password) VALUES (?, ?, ?)
        ''', (name, email, password))
        conn.commit()
        return "Администратор успешно добавлен!"
    except sqlite3.IntegrityError:
        return "Ошибка: Невозможно зарегистрировать администратора."
    finally:
        conn.close()

def add_client(name, phone, address):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO clients (name, phone, address)
            VALUES (?, ?, ?)
        ''', (name, phone, address))
        conn.commit()
        client_id = cur.lastrowid
        logging.info(f"Клиент с ID {client_id} успешно добавлен.")
        return client_id
    except sqlite3.Error as e:
        logging.error(f"Ошибка добавления клиента: {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_order(order_id, client_id, disinsector_id=None, object_type=None, insect_quantity=None,
              disinsect_experience=None, status='Новая'):
    try:
        with sqlite3.connect('disinsect_data.db') as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO orders (
                    client_id, order_id, disinsector_id, object_type, insect_quantity,
                    disinsect_experience, order_status, order_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, date('now'))
            ''', (client_id, order_id, disinsector_id, object_type, insect_quantity,
                  disinsect_experience, status))
            conn.commit()
            logging.info(f"Заявка с order_id {order_id} успешно добавлена.")
            return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении заявки: {e}")
        return False


def update_order(order_id, estimated_price=None, final_price=None, poison_type=None, insect_type=None,
                 client_area=None, order_status=None, disinsector_id=None, name=None, object_type=None,
                 insect_quantity=None, disinsect_experience=None, phone=None, address=None):
    try:
        with sqlite3.connect('disinsect_data.db') as conn:
            cur = conn.cursor()
            fields = []
            values = []

            if estimated_price is not None:
                fields.append("estimated_price = ?")
                values.append(estimated_price)

            if final_price is not None:
                fields.append("final_price = ?")
                values.append(final_price)

            if poison_type is not None:
                fields.append("poison_type = ?")
                values.append(poison_type)

            if insect_type is not None:
                fields.append("insect_type = ?")
                values.append(insect_type)

            if client_area is not None:
                fields.append("client_area = ?")
                values.append(client_area)

            if order_status is not None:
                fields.append("order_status = ?")
                values.append(order_status)

            if disinsector_id is not None:
                fields.append("disinsector_id = ?")
                values.append(disinsector_id)

            if name is not None:
                fields.append("name = ?")
                values.append(name)

            if object_type is not None:
                fields.append("object_type = ?")
                values.append(object_type)

            if insect_quantity is not None:
                fields.append("insect_quantity = ?")
                values.append(insect_quantity)

            if disinsect_experience is not None:
                fields.append("disinsect_experience = ?")
                values.append(disinsect_experience)

            if phone is not None:
                fields.append("phone = ?")
                values.append(phone)

            if address is not None:
                fields.append("address = ?")
                values.append(address)

            if fields:
                sql = f"UPDATE orders SET {', '.join(fields)} WHERE order_id = ?"
                values.append(order_id)
                cur.execute(sql, values)
                conn.commit()
                return True
            else:
                return False
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении заявки {order_id}: {e}")
        return False


# Функция для получения всех токенов дезинсекторов
def get_all_disinsector_tokens():
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('SELECT token FROM disinsectors')
        tokens = [row[0] for row in cur.fetchall()]
        return tokens
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении всех токенов дезинсекторов: {e}")
        return []
    finally:
        if conn:
            conn.close()



def get_disinsector_by_token(token):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM disinsectors WHERE token = ?', (token,))
        disinsector = cur.fetchone()
        return disinsector
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении дезинсектора по токену: {e}")
        return None
    finally:
        if conn:
            conn.close()

# В db.py
def update_disinsector_user_id(disinsector_id, user_id):
    try:
        with sqlite3.connect('disinsect_data.db') as conn:
            cur = conn.cursor()
            cur.execute("UPDATE disinsectors SET user_id = ? WHERE id = ?", (user_id, disinsector_id))
            conn.commit()
            logging.info(f"user_id для дезинсектора {disinsector_id} обновлен на {user_id}")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении user_id дезинсектора {disinsector_id}: {e}")



init_db()
