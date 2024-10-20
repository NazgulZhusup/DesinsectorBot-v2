import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import keyboards as kb
from db import get_disinsector_by_token, get_all_disinsector_tokens, update_order
import sqlite3
from config import TOKEN

# Инициализация бота дезинсектора
storage = MemoryStorage()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disinsector_bot.log"),
        logging.StreamHandler()
    ]
)

class DisinsectorForm(StatesGroup):
    poison_type = State()
    insect_type = State()
    client_area = State()
    estimated_price = State()

async def start_disinsector_bot(token):
    logging.info(f"Starting disinsector bot with token: {token}")
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)

    # Стартовая команда
    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        try:
            disinsector = get_disinsector_by_token(token)
            if disinsector:
                user_id = message.from_user.id
                await message.answer(f"Добро пожаловать, {disinsector[1]}! Ваш user_id: {user_id}")

                await state.update_data(disinsector_id=disinsector[0])

                # Отправляем вопрос с кнопками
                logging.info(f"Disinsector {disinsector[1]} ({disinsector[0]}) logged in")
                await message.answer("Какой химикат будет использоваться?", reply_markup=kb.inl_kb_poison_type)
                await state.set_state(DisinsectorForm.poison_type)
            else:
                await message.answer("Ошибка авторизации.")
        except Exception as e:
            logging.error(f"Error during the start command: {e}")

    # Обработчик выбора химиката
    @dp.callback_query(F.data.startswith('poison_'))
    async def process_poison_selection(callback: types.CallbackQuery, state: FSMContext):
        try:
            poison_type = callback.data.split('_')[1]
            await state.update_data(poison_type=poison_type)
            await callback.answer()

            # Задаем следующий вопрос
            await callback.message.answer("Какой вид насекомого?", reply_markup=kb.inl_kb_insect_type)
            await state.set_state(DisinsectorForm.insect_type)
        except Exception as e:
            logging.error(f"Error during poison selection: {e}")

    # Обработчик выбора насекомого
    @dp.callback_query(F.data.startswith('insect_'))
    async def process_insect_selection(callback: types.CallbackQuery, state: FSMContext):
        try:
            insect_type = callback.data.split('_')[1]
            await state.update_data(insect_type=insect_type)
            await callback.answer()

            # Вопрос о площади помещения
            await callback.message.answer("Какова площадь помещения? Введите числовое значение.")
            await state.set_state(DisinsectorForm.client_area)
        except Exception as e:
            logging.error(f"Error during insect selection: {e}")

    # Обработчик ввода площади помещения
    @dp.message(DisinsectorForm.client_area)
    async def process_client_area(message: types.Message, state: FSMContext):
        try:
            client_area = float(message.text)
            await state.update_data(client_area=client_area)
            logging.info(f"Client area successfully parsed: {client_area}")

            # Вопрос о предварительной стоимости
            await message.answer("Какова предварительная стоимость? Введите числовое значение.")
            await state.set_state(DisinsectorForm.estimated_price)
        except ValueError:
            logging.error(f"Failed to parse client area: {message.text}")
            await message.answer("Пожалуйста, введите числовое значение.")
        except Exception as e:
            logging.error(f"Error during client area processing: {e}")

    # Обработчик ввода предварительной стоимости
    @dp.message(DisinsectorForm.estimated_price)
    async def process_estimated_price(message: types.Message, state: FSMContext):
        try:
            estimated_price = float(message.text)
            await state.update_data(estimated_price=estimated_price)

            # Получаем все данные из состояния
            user_data = await state.get_data()
            poison_type = user_data.get('poison_type')
            insect_type = user_data.get('insect_type')
            client_area = user_data.get('client_area')
            order_id = user_data.get('order_id')  # Предположим, что order_id уже передан ранее

            # Обновляем заявку в базе данных
            update_order(
                order_id=order_id,
                poison_type=poison_type,
                insect_type=insect_type,
                client_area=client_area,
                estimated_price=estimated_price
            )

            await message.answer(
                f"Данные заявки {order_id} обновлены:\n"
                f"Химикат: {poison_type}\n"
                f"Вид насекомого: {insect_type}\n"
                f"Площадь помещения: {client_area} кв.м\n"
                f"Предварительная стоимость: {estimated_price} рублей"
            )

            # Очищаем состояние
            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите числовое значение для стоимости.")
        except Exception as e:
            logging.error(f"Error during estimated price processing: {e}")

    await dp.start_polling(bot)

async def main():
    try:
        tasks = []
        # Получаем все токены дезинсекторов и запускаем их ботов
        disinsector_tokens = get_all_disinsector_tokens()
        if not disinsector_tokens:
            logging.error("No disinsector tokens found.")
        for token in disinsector_tokens:
            tasks.append(start_disinsector_bot(token))

        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Error in main function: {e}")

if __name__ == '__main__':
    asyncio.run(main())
