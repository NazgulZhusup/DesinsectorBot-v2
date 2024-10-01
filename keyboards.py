# keyboards.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# Клавиатура приветствия с кнопкой "Начать"
inl_kb_greetings = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Начать", callback_data="start")]
])

# Клавиатура выбора объекта
inl_kb_object = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дом", callback_data="object_home")],
    [InlineKeyboardButton(text="Квартира", callback_data="object_apartment")],
    [InlineKeyboardButton(text="Офис", callback_data="object_office")]
])

# Клавиатура выбора количества насекомых
inl_kb_insect_quantity = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Менее 50", callback_data="quantity_less_50")],
    [InlineKeyboardButton(text="50-200", callback_data="quantity_50_200")],
    [InlineKeyboardButton(text="Более 200", callback_data="quantity_more_200")]
])

# Клавиатура выбора опыта дезинсекции
inl_kb_experience = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="experience_yes")],
    [InlineKeyboardButton(text="Нет", callback_data="experience_no")]
])

# Клавиатура для сбора контакта
kb_contact = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Отправить контакт", request_contact=True)
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
