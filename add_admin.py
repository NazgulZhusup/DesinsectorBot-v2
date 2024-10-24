from db import init_db, add_admin

# Инициализируем базу данных (это создаст таблицы, если они еще не созданы)
init_db()

# Добавляем администратора в базу данных
result = add_admin('Admin Name', 'admin@example.com', '123456')
print(result)