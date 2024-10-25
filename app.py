import asyncio
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3
import csv
from io import StringIO
import logging
from shared_functions import send_notification_to_disinsector_and_start_questions, get_disinsector_token
from db import add_admin, get_disinsector_by_token, update_disinsector_user_id
from aiogram import Bot
from config import TOKEN

# Инициализация приложения
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("web_app.log"),
        logging.StreamHandler()
    ]
)

@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для регистрации дезинсектора (только для администратора)
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

            # Проверка, существует ли уже такой email в таблице disinsectors
            cur.execute("SELECT * FROM disinsectors WHERE email = ?", (email,))
            existing_disinsector = cur.fetchone()

            if existing_disinsector:
                flash('Ошибка: Этот email уже используется.')
                return redirect(url_for('admin_dashboard'))

            try:
                # Вставляем данные в таблицу disinsectors
                cur.execute('''
                    INSERT INTO disinsectors (name, email, password, token)
                    VALUES (?, ?, ?, ?)
                ''', (name, email, password, token))
                conn.commit()
                flash(f"Дезинсектор {name} успешно зарегистрирован!")
            except sqlite3.IntegrityError as e:
                logging.error(f"Ошибка при регистрации дезинсектора: {e}")
                flash('Ошибка: Этот токен уже используется другим дезинсектором.')
            finally:
                conn.close()

            return redirect(url_for('admin_dashboard'))

        return render_template('register_disinsector.html')
    else:
        return redirect(url_for('admin_login'))


# Маршрут для входа дезинсектора по токену
@app.route('/disinsector/login', methods=['GET', 'POST'])
def disinsector_login():
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


# Маршрут для регистрации администратора
@app.route('/admin/register', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        result = add_admin(name, email, password)

        flash(result)

        return redirect(url_for('admin_login'))

    return render_template('register_admin.html')

# Маршрут для входа администратора
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

# Дашборд администратора
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    logging.info(f"Session: {session}")

    if 'user_id' in session and session.get('role') == 'admin':
        logging.info("Admin authenticated")

        try:
            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()

            # Получаем заявки с необходимыми полями, присоединяя таблицу clients
            cur.execute('''
                SELECT o.order_id, c.name, c.phone, c.address, o.order_status,
                       o.estimated_price, o.final_price, o.poison_type, o.insect_type, o.insect_quantity
                FROM orders o
                JOIN clients c ON o.client_id = c.id
            ''')

            orders = cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Ошибка базы данных: {e}")
            flash("Ошибка при получении данных из базы.")
            return redirect(url_for('admin_dashboard'))
        finally:
            conn.close()

        if orders:
            return render_template('admin_dashboard.html', orders=orders, filter_status='Все')
        else:
            flash("Нет заявок для отображения")
            return render_template('admin_dashboard.html', orders=[], filter_status='Все')

    else:
        logging.warning("Unauthorized access attempt to /admin/dashboard")
        return redirect(url_for('admin_login'))

# Дашборд дезинсектора
@app.route('/disinsector/dashboard', methods=['GET', 'POST'])
def disinsector_dashboard():
    if 'user_id' in session and session.get('role') == 'disinsector':
        disinsector_id = session.get('user_id')

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Если был отправлен запрос на обновление статуса
        if request.method == 'POST':
            order_id = request.form['order_id']
            new_status = request.form['status']
            cur.execute("UPDATE orders SET order_status = ? WHERE order_id = ?", (new_status, order_id))
            conn.commit()

        # Получаем все заявки, связанные с дезинсектором, присоединяя таблицу clients
        cur.execute('''
            SELECT o.order_id, c.name, c.phone, c.address, o.order_status,
                   o.estimated_price, o.final_price, o.poison_type, o.insect_type, o.client_area
            FROM orders o
            JOIN clients c ON o.client_id = c.id
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
        return redirect(url_for('disinsector_login'))

# Обновление статуса заявки (только для дезинсектора)
@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' in session and session.get('role') == 'disinsector':
        order_id = request.form['order_id']
        new_status = request.form['new_status']

        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('UPDATE orders SET order_status = ? WHERE order_id = ?', (new_status, order_id))
        conn.commit()
        conn.close()

        # Можно добавить отправку уведомления клиенту, если требуется

        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})

# Маршрут для экспорта заявок в CSV (только для администратора)
@app.route('/export_csv')
def export_csv():
    if 'user_id' in session and session.get('role') == 'admin':
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute('''
            SELECT c.name, c.phone, c.address, o.order_status
            FROM orders o
            JOIN clients c ON o.client_id = c.id
        ''')
        orders = cur.fetchall()
        conn.close()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Имя', 'Телефон', 'Адрес', 'Статус'])

        for order in orders:
            writer.writerow(order)

        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=orders.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    else:
        return redirect(url_for('admin_login'))

# Маршрут для экспорта заявок в JSON (только для администратора)

@app.route('/export_json')
def export_json():
    if 'user_id' in session and session.get('role') == 'admin':
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Извлекаем все данные из таблицы orders
        cur.execute('''
            SELECT order_id, client_id, disinsector_id, name, object, insect_quantity, disinsect_experience,
                   phone, address, order_status, order_date, estimated_price, final_price, poison_type, insect_type, client_area
            FROM orders
        ''')
        orders = cur.fetchall()

        # Закрываем соединение с базой данных
        conn.close()

        # Преобразуем полученные данные в формат JSON
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order[0],
                'client_id': order[1],
                'disinsector_id': order[2],
                'name': order[3],
                'object': order[4],
                'insect_quantity': order[5],
                'disinsect_experience': order[6],
                'phone': order[7],
                'address': order[8],
                'order_status': order[9],
                'order_date': order[10],
                'estimated_price': order[11],
                'final_price': order[12],
                'poison_type': order[13],
                'insect_type': order[14],
                'client_area': order[15]
            })

        # Возвращаем данные в формате JSON
        return jsonify(orders_list)
    else:
        return redirect(url_for('admin_login'))


# Маршрут для отчетов администратора
@app.route('/admin/reports', methods=['GET', 'POST'])
def admin_reports():
    if 'user_id' in session and session.get('role') == 'admin':
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        disinsectors = []
        data_list = []

        # Получаем список дезинсекторов
        cur.execute("SELECT id, name FROM disinsectors")
        disinsectors = cur.fetchall()

        if request.method == 'POST':
            disinsector_filter = request.form.get('disinsector')

            query = '''
                SELECT d.id, d.name,
                       COUNT(o.id) AS ordersTotal,
                       SUM(CASE WHEN o.order_status = 'Выполнено' THEN 1 ELSE 0 END) AS ordersDone,
                       SUM(CASE WHEN o.order_status = 'В процессе' THEN 1 ELSE 0 END) AS ordersWait,
                       o.order_id, o.order_status, o.order_date, o.estimated_price, o.final_price,
                       o.poison_type, c.name, o.insect_type, o.insect_quantity,
                       c.phone, c.address, o.client_area
                FROM disinsectors d
                LEFT JOIN orders o ON d.id = o.disinsector_id
                LEFT JOIN clients c ON o.client_id = c.id
            '''

            params = []
            if disinsector_filter and disinsector_filter != 'Все':
                query += " WHERE d.id = ?"
                params.append(disinsector_filter)

            query += " GROUP BY d.id, o.order_id"

            cur.execute(query, params)
            results = cur.fetchall()

            if 'export_json' in request.form:
                return export_detailed_json(results)

        conn.close()
        return render_template('admin_reports.html', disinsectors=disinsectors)
    else:
        return redirect(url_for('admin_login'))

# Экспорт детализированных данных в JSON
def export_detailed_json(data):
    data_list = []
    current_disinsector = None
    disinsector_info = {}

    for row in data:
        (user_id, user_name, orders_total, orders_done, orders_wait, order_id, order_status,
         order_date, estimated_price, final_price, poison_type, client_name, insect_type,
         insect_quantity, phone, address, client_area) = row

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
            "clientName": client_name,
            "insectType": insect_type,
            "insectQuant": insect_quantity,
            "clientPhone": phone,
            "clientAddress": address,
            "clientArea": client_area
        })

    # Добавляем последнего дезинсектора, если есть данные
    if current_disinsector is not None:
        data_list.append(disinsector_info)

    # Возвращаем JSON
    response = make_response(jsonify(data_list))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Основной запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
