import asyncio
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3
import csv
from io import StringIO
from aiogram import Bot
from config import TOKEN

# Инициализация приложения
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Инициализация бота
bot = TOKEN


@app.route('/')
def index():
    return render_template('index.html')

# Функция для проверки пользователя в базе данных
def check_user(token, password):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM disinsectors WHERE token = ? AND password = ?", (token, password))
    user = cur.fetchone()
    conn.close()
    return user

@app.route('/register_disinsector', methods=['GET', 'POST'])
def register_disinsector():
    if 'user_id' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            token = request.form['token']

            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()

            # Проверка, существует ли уже такой email
            cur.execute("SELECT * FROM admins WHERE email = ?", (email,))
            admin = cur.fetchone()

            if admin:
                flash('Ошибка: Этот email уже используется.')
                return redirect(url_for('admin_dashboard'))

            try:
                # Вставляем данные во все обязательные поля таблицы disinsectors
                cur.execute('''
                    INSERT INTO disinsectors (name, email, password, token) 
                    VALUES (?, ?, ?, ?)
                ''', (name, email, password, token))
                conn.commit()
                flash(f"Дезинсектор {name} успешно зарегистрирован!")
            except sqlite3.IntegrityError:
                flash('Ошибка: Этот токен уже используется другим дезинсектором.')
            finally:
                conn.close()

            return redirect(url_for('admin_dashboard'))

        return render_template('admin_dashboard.html')
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['POST'])
def login():
    token = request.form.get('token')
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM disinsectors WHERE token = ?", (token,))
    disinsector = cur.fetchone()

    conn.close()

    if disinsector:
        session['disinsector_id'] = disinsector[0]
        session['role'] = 'disinsector'
        return redirect(url_for('disinsector_dashboard'))
    else:
        flash('Неверный токен, попробуйте снова.')
        return redirect(url_for('login'))

@app.route('/disinsector/login', methods=['GET', 'POST'])
def disinsector_login():
    if 'disinsector_id' in session and session.get('role') == 'disinsector':

        if request.method == 'POST':
            token = request.form.get('token')

            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()

            cur.execute("SELECT id, name FROM disinsectors WHERE token = ?", (token,))
            disinsector = cur.fetchone()
            conn.close()

            if disinsector:
                session['user_id'] = disinsector[0]
                session['role'] = 'disinsector'
                return redirect(url_for('disinsector_dashboard'))
            else:
                flash('Неверный токен, попробуйте снова.')
                return redirect(url_for('disinsector_login'))

    return render_template('disinsector_login.html')


@app.route('/admin/register', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Проверка на уникальность email
        cur.execute('SELECT * FROM admins WHERE email = ?', (email,))
        existing_admin = cur.fetchone()

        if existing_admin:
            flash('Ошибка: Этот email уже используется.')
        else:
            try:
                cur.execute('''
                    INSERT INTO admins (name, email, password) VALUES (?, ?, ?)
                ''', (name, email, password))
                conn.commit()
                flash(f"Администратор {name} успешно зарегистрирован!")
            except sqlite3.IntegrityError:
                flash('Ошибка: Невозможно зарегистрировать администратора.')
            finally:
                conn.close()

        return redirect(url_for('admin_login'))

    return render_template('register_admin.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM admins WHERE email = ? AND password = ?", (email, password))
        admin = cur.fetchone()
        conn.close()

        if admin:
            session['user_id'] = admin[0]
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверные данные, попробуйте снова.')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' in session and session.get('role') == 'admin':
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Получаем заявки с необходимыми полями
        cur.execute('''
            SELECT o.order_id, u.name, u.phone, u.address, o.order_status, o.estimated_price, o.final_price, 
                   o.poison_type, o.insect_type, o.insect_quantity
            FROM orders o
            JOIN users u ON o.client_id = u.id
        ''')

        clients = cur.fetchall()
        conn.close()

        if clients:
            return render_template('admin_dashboard.html', clients=clients, filter_status='Все')
        else:
            flash("Нет заявок для отображения")
            return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))


def get_disinsector_token(disinsector_id):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute("SELECT token FROM disinsectors WHERE id = ?", (disinsector_id,))
    token = cur.fetchone()
    conn.close()
    return token[0] if token else None  # Возвращаем токен дезинсектора или None, если токен не найден


# Панель управления дезинсектора
@app.route('/disinsector/dashboard', methods=['GET', 'POST'])
def disinsector_dashboard():
    if 'disinsector_id' in session and session.get('role') == 'disinsector':
        disinsector_id = session.get('disinsector_id')

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Если был отправлен запрос на обновление статуса
        if request.method == 'POST':
            order_id = request.form['order_id']
            new_status = request.form['status']
            cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
            conn.commit()

        # Получаем все заявки, связанные с дезинсектором
        cur.execute('''
                    SELECT o.order_id, u.name, u.phone, u.address, o.order_status, o.estimated_price, o.final_price, 
                           o.poison_type, o.insect_type, o.insect_quantity
                    FROM orders o
                    JOIN users u ON o.client_id = u.id
                    WHERE o.disinsector_id = ?
                ''', (disinsector_id,))
        orders = cur.fetchall()

        conn.close()

        if orders:
            return render_template('disinsector_dashboard.html', orders=orders)
        else:
            flash("На данный момент у вас нет заявок.")
            return render_template('disinsector_dashboard.html', orders=[])

    else:
        return redirect(url_for('login'))

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' in session and session.get('role') == 'disinsector':
        order_id = request.form['order_id']
        new_status = request.form['new_status']

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('UPDATE orders SET order_status = ? WHERE id = ?', (new_status, order_id))
        conn.commit()

        # Отправка уведомления через Телеграм
        disinsector_id = request.form.get('disinsector_id')
        if disinsector_id:
            message_text = f"Статус вашей заявки {order_id} изменен на {new_status}."
            asyncio.run(send_notification_to_disinsector(disinsector_id, message_text))

        conn.close()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})

# Функция отправки уведомления дезинсектору
async def send_notification_to_disinsector(disinsector_id, chat_id, message_text):
    token = get_disinsector_token(disinsector_id)
    if token:
        bot = Bot(token=token)  # Создаем экземпляр бота с динамическим токеном
        await bot.send_message(chat_id=chat_id, text=message_text)
    else:
        print(f"Не удалось найти токен для дезинсектора с ID {disinsector_id}")

# Пример использования после обновления статуса заявки
    disinsector_id = 1  # ID дезинсектора, к которому привязана заявка
    chat_id = 123456789  # Телеграм ID чата дезинсектора
    message_text = "Статус вашей заявки изменен на 'Выполнено'."

    await send_notification_to_disinsector(disinsector_id, chat_id, message_text)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    client_name = data.get('client_name')
    order_id = data.get('order_id')
    status = data.get('order_status')
    disinsector_id = data.get('disinsector_id')

    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO orders (client_name, order_id, order_status, disinsector_id)
        VALUES (?, ?, ?, ?)
    ''', (client_name, order_id, status, disinsector_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok'})



# Экспорт заявок в CSV
@app.route('/export_csv')
def export_csv():
    if 'disinsector_id' in session:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute("SELECT name, phone, address, status FROM users")
        clients = cur.fetchall()
        conn.close()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Имя', 'Телефон', 'Адрес', 'Статус'])

        for client in clients:
            writer.writerow(client)

        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=clients.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    else:
        return redirect(url_for('login'))


# Экспорт заявок в JSON
@app.route('/export_json')
def export_json():
    if 'disinsector_id' in session:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute("SELECT name, phone, address, status FROM users")
        clients = cur.fetchall()
        conn.close()

        clients_list = []
        for client in clients:
            clients_list.append({
                'name': client[0],
                'phone': client[1],
                'address': client[2],
                'status': client[3]
            })

        return jsonify(clients_list)
    else:
        return redirect(url_for('login'))


# Маршрут для администраторских отчетов
@app.route('/admin/reports', methods=['GET', 'POST'])
def admin_reports():
    if 'user_id' in session and session.get('role') == 'admin':
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        if request.method == 'POST':
            disinsector_filter = request.form.get('disinsector')

            query = '''
                SELECT d.id, d.name, 
                       COUNT(o.id) AS ordersTotal,
                       SUM(CASE WHEN o.order_status = 'Выполнено' THEN 1 ELSE 0 END) AS ordersDone,
                       SUM(CASE WHEN o.order_status = 'В процессе' THEN 1 ELSE 0 END) AS ordersWait,
                       o.order_id, o.order_status, o.order_date, o.estimated_price, o.final_price, 
                       o.poison_type, o.client_name, o.insect_type, o.insect_quantity, 
                       o.client_contact, o.client_address, o.client_property_type, o.client_area
                FROM disinsectors d
                LEFT JOIN orders o ON d.id = o.user_id
            '''

            if disinsector_filter and disinsector_filter != 'Все':
                query += " WHERE d.id = ?"
                cur.execute(query, (disinsector_filter,))
            else:
                cur.execute(query)

            results = cur.fetchall()

            if 'export_json' in request.form:
                return export_detailed_json(results)

        cur.execute("SELECT id, name FROM disinsectors")
        disinsectors = cur.fetchall()

        conn.close()
        return render_template('admin_reports.html', disinsectors=disinsectors)
    else:
        return redirect(url_for('login'))


from flask import jsonify

def export_detailed_json(data):
    data_list = []
    current_disinsector = None
    disinsector_info = {}

    for row in data:
        user_id, user_name, orders_total, orders_done, orders_wait, order_id, order_status, order_date, estimated_price, final_price, poison_type, client_name, insect_type, insect_quantity, client_contact, client_address, client_property_type, client_area = row

        # Если мы перешли к новому дезинсектору, добавляем предыдущего в список
        if current_disinsector != user_id:
            if current_disinsector is not None:
                data_list.append(disinsector_info)

            disinsector_info = {
                "userid": user_id,
                "userName": user_name,
                "ordersTotal": orders_total,
                "ordersDone": orders_done,
                "ordersWait": orders_wait,
                "orders": []
            }
            current_disinsector = user_id

        # Добавляем данные по каждому заказу
        disinsector_info["orders"].append({
            "orderId": order_id,
            "orderStatus": order_status,
            "orderDate": order_date,
            "orderEstPrice": estimated_price,
            "orderFinalPrice": final_price,
            "poisonType": poison_type,
            "userid": user_id,
            "clientName": client_name,
            "insectType": insect_type,
            "insectQuant": insect_quantity,
            "clientContact": client_contact,
            "clientAdress": client_address,
            "clientPropertyType": client_property_type,
            "clientArea": client_area
        })

    # Добавляем последнего дезинсектора, если есть данные
    if current_disinsector is not None:
        data_list.append(disinsector_info)

    # Возвращаем JSON с ensure_ascii=False, чтобы поддерживать русский текст
    return jsonify(data_list, ensure_ascii=False)

# Маршрут для обновления статуса заявки и отправки уведомления


# Выход из системы
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

# Функция для отправки сообщений через Телеграм
async def send_notification_to_disinsector(chat_id, message_text):
    await bot.send_message(chat_id=chat_id, text=message_text)

# Основной запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
