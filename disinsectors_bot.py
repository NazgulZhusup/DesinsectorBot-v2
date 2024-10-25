import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import keyboards as kb
from db import get_disinsector_by_token, update_order, get_all_disinsector_tokens
from shared_functions import get_disinsector_token

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
    order_id = State()


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
                disinsector_id = disinsector[0]
                # Сохраняем user_id дезинсектора в базе данных
                from db import update_disinsector_user_id
                update_disinsector_user_id(disinsector_id, user_id)
                await state.update_data(disinsector_id=disinsector_id)
                await message.answer(f"Добро пожаловать, {disinsector[1]}!")
                logging.info(f"Disinsector {disinsector[1]} ({disinsector_id}) registered with user_id {user_id}")
            else:
                await message.answer("Ошибка авторизации. Некорректный токен.")
        except Exception as e:
            logging.error(f"Error during the start command: {e}")

    # Обработчик уведомления о новой заявке
    @dp.callback_query(lambda c: c.data.startswith('accept_order_'))
    async def process_accept_order(callback: types.CallbackQuery, state: FSMContext):
        order_id = callback.data.split('_')[-1]  # Извлекаем order_id
        await state.update_data(order_id=order_id)
        await callback.answer()
        await callback.message.answer("Какой химикат будет использоваться?", reply_markup=kb.inl_kb_poison_type)
        await state.set_state(DisinsectorForm.poison_type)

    @dp.callback_query(lambda c: c.data.startswith('decline_order_'))
    async def process_decline_order(callback: types.CallbackQuery, state: FSMContext):
        order_id = callback.data.split('_')[-1]  # Извлекаем order_id
        # Обновляем статус заявки в базе данных
        update_order(order_id=order_id, order_status='Отклонена')
        await callback.answer("Вы отказались от заявки.", show_alert=True)
        await state.clear()

    # Обработчик выбора химиката
    @dp.callback_query(F.data.startswith('poison_'))
    async def process_poison_selection(callback: types.CallbackQuery, state: FSMContext):
        poison_type = callback.data.split('_')[1]
        await state.update_data(poison_type=poison_type)
        await callback.answer()
        await callback.message.answer("Какой вид насекомого?", reply_markup=kb.inl_kb_insect_type)
        await state.set_state(DisinsectorForm.insect_type)

    # Обработчик выбора насекомого
    @dp.callback_query(F.data.startswith('insect_'))
    async def process_insect_selection(callback: types.CallbackQuery, state: FSMContext):
        insect_type = callback.data.split('_')[1]
        await state.update_data(insect_type=insect_type)
        await callback.answer()
        await callback.message.answer("Какова площадь помещения? Введите числовое значение.")
        await state.set_state(DisinsectorForm.client_area)

    # Обработчик ввода площади помещения
    @dp.message(DisinsectorForm.client_area)
    async def process_client_area(message: types.Message, state: FSMContext):
        try:
            client_area = float(message.text)
            await state.update_data(client_area=client_area)
            await message.answer("Какова предварительная стоимость? Введите числовое значение.")
            await state.set_state(DisinsectorForm.estimated_price)
        except ValueError:
            await message.answer("Пожалуйста, введите числовое значение.")

    @dp.message(DisinsectorForm.estimated_price)
    async def process_estimated_price(message: types.Message, state: FSMContext):
        try:
            estimated_price = float(message.text)
            await state.update_data(estimated_price=estimated_price)
            user_data = await state.get_data()

            order_id = user_data.get('order_id')
            if not order_id:
                await message.answer("Ошибка: отсутствует номер заявки. Пожалуйста, начните процесс заново.")
                return

            poison_type = user_data.get('poison_type')
            insect_type = user_data.get('insect_type')
            client_area = user_data.get('client_area')
            disinsector_id = user_data.get('disinsector_id')

            if not all([poison_type, insect_type, client_area, disinsector_id]):
                await message.answer("Ошибка: отсутствуют необходимые данные для обновления заказа. Пожалуйста, начните заново.")
                return

            # Обновляем заявку в базе данных
            success = update_order(
                order_id=order_id,
                estimated_price=estimated_price,
                poison_type=poison_type,
                insect_type=insect_type,
                client_area=client_area,
                order_status='В процессе',
                disinsector_id=disinsector_id
            )

            if success:
                await message.answer(
                    f"Данные заявки обновлены:\n"
                    f"Химикат: {poison_type}\n"
                    f"Вид насекомого: {insect_type}\n"
                    f"Площадь помещения: {client_area} кв.м\n"
                    f"Предварительная стоимость: {estimated_price} рублей"
                )
            else:
                await message.answer("Ошибка при обновлении заявки. Пожалуйста, попробуйте снова.")

            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите числовое значение для стоимости.")

    await dp.start_polling(bot)


async def main():
    try:
        tasks = []
        tokens = get_all_disinsector_tokens()
        if not tokens:
            logging.error("Нет токенов дезинсекторов для запуска ботов.")
            return
        for token in tokens:
            tasks.append(start_disinsector_bot(token))
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Ошибка в основной функции: {e}")


if __name__ == '__main__':
    asyncio.run(main())
