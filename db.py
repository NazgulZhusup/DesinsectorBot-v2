import sqlite3
import logging

def init_db():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Таблица для хранения заявок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER, -- Ссылка на клиента
            disinsector_id INTEGER, -- Ссылка на дезинсектора
            order_id TEXT NOT NULL,
            name TEXT, -- Имя клиента
            object TEXT, -- Объект клиента
            insect_quantity TEXT, -- Количество насекомых
            disinsect_experience TEXT, -- Опыт дезинсекции клиента
            phone TEXT, -- Телефон клиента
            address TEXT, -- Адрес клиента
            order_status TEXT DEFAULT 'Новая', -- Статус заявки
            order_date TEXT,
            estimated_price REAL,
            final_price REAL,
            poison_type TEXT,
            insect_type TEXT,
            client_area REAL,
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

# Функция для добавления нового клиента в таблицу orders
def add_client(name, object, insect_quantity, disinsect_experience, phone, address):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO orders (name, object, insect_quantity, disinsect_experience, phone, address, order_status, order_date)
            VALUES (?, ?, ?, ?, ?, ?, 'Новая', date('now'))
        ''', (name, object, insect_quantity, disinsect_experience, phone, address))
        conn.commit()
        client_id = cur.lastrowid
        conn.close()
        return client_id
    except sqlite3.Error as e:
        logging.error(f"Ошибка добавления клиента: {e}")
        return None

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
# Функция для получения дезинсектора по токену
def get_disinsector_by_token(token):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM disinsectors WHERE token = ?', (token,))
        disinsector = cur.fetchone()
        conn.close()
        return disinsector
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении дезинсектора по токену: {e}")
        return None

# Функция для получения всех токенов дезинсекторов
def get_all_disinsector_tokens():
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('SELECT token FROM disinsectors')
        tokens = [row[0] for row in cur.fetchall()]
        conn.close()
        return tokens
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении всех токенов дезинсекторов: {e}")
        return []


def add_order(order_id, client_id=None, disinsector_id=None, name=None, object_type=None, insect_quantity=None,
              disinsect_experience=None, phone=None, address=None, status='Новая'):
    try:
        with sqlite3.connect('disinsect_data.db') as conn:
            cur = conn.cursor()

            # Логирование данных перед записью
            logging.info(f"Создание/добавление заказа для client_id={client_id}, disinsector_id={disinsector_id}, order_id={order_id}")

            cur.execute('''
                INSERT INTO orders (
                    client_id, order_id, disinsector_id, name, object, insect_quantity, 
                    disinsect_experience, phone, address, order_status, order_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'))
            ''', (client_id, order_id, disinsector_id, name, object_type, insect_quantity, disinsect_experience, phone, address, status))

            conn.commit()
            logging.info(f"Заявка с order_id {order_id} успешно добавлена.")
            return True  # Возвращаем True при успешном выполнении
    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении заявки: {e}, order_id: {order_id}, disinsector_id: {disinsector_id}")
        return False  # Возвращаем False при ошибке



def update_order(estimated_price, final_price, poison_type, insect_type, client_area, order_status, order_id):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Включаем отладочное логирование SQL-запросов
        conn.set_trace_callback(logging.info)

        # Проверка существования заказа перед обновлением
        cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order_exists = cur.fetchone()

        if not order_exists:
            logging.error(f"Ошибка: заказ с order_id {order_id} не существует.")
            return False

        # Логирование перед обновлением
        logging.info(f"Обновляем заявку {order_id} с данными: poison_type={poison_type}, insect_type={insect_type}, client_area={client_area}, estimated_price={estimated_price}, final_price={final_price}, order_status={order_status}")

        # Выполнение обновления
        cur.execute('''
            UPDATE orders
            SET estimated_price = ?, final_price = ?, poison_type = ?, insect_type = ?, client_area = ?, order_status = ?  
            WHERE order_id = ?
        ''', (estimated_price, final_price, poison_type, insect_type, client_area, order_status, order_id))

        # Проверка успешности обновления
        if cur.rowcount == 0:
            logging.error(f"Заявка с order_id {order_id} не была обновлена.")
        else:
            logging.info(f"Заявка {order_id} успешно обновлена.")

        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении заявки {order_id}: {e}")
        return False

    finally:

        conn.close()

    return True




# Инициализация базы данных при первом запуске
init_db()
