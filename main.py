from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
import sqlite3

API_TOKEN = '1027107975:AAGHHW2D9AVBaadxALkn2z1Rh5YPdnEliKE'
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


class ClientStatesGroup(StatesGroup):
    add_channels_state = State()
    add_keywords_state = State()
    remove_channel_state = State()
    remove_keywords_state = State()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton('Получить посты'))
    kb.add(KeyboardButton('Добавить чат/канал для поиска'), KeyboardButton('Добавить ключевые слова'))
    kb.add(KeyboardButton('Удалить чат/канал из поиска'), KeyboardButton('Удалить ключевые слова'))
    return kb


def get_change_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Отмена'))
    return kb


@dp.message_handler(commands=['start', 'help'])
async def welcome(message: types.Message):
    await bot.send_message(message.chat.id, '''Привет.
Поиск осуществляется автоматически по каналам и ключевым словам, которые ты укажешь.
Я делаю поиск раз в час, получить же актуальные посты можно с помощью кнопки "Получить посты".
''', reply_markup=get_main_keyboard())


@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def go_to_main_menu(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    await message.answer('Главное меню', reply_markup=get_main_keyboard())
    await state.finish()


@dp.message_handler(Text(equals='Получить посты', ignore_case=True))
async def get_data(message: types.Message) -> None:
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    try:
        cursor.execute(
            f'''SELECT * FROM search_results
                WHERE is_frozen == 0 and search_user = {message.chat.id}'''
        )

        data = [elem for elem in cursor.fetchall()]

        if data:
            id_list = [elem[0] for elem in data]

            for result in data:
                await bot.send_message(message.chat.id, text=f'{result[2]}\n\n'  # Дата
                                                             f'{result[4]}\n'  # Текст
                                                             f'--------------------\n\n'
                                                             f'{result[5]}\n'  # Ссылка
                                                             f'{result[3]}\n'  # Username

                                       )

            query = f"UPDATE search_results SET is_frozen = 1 WHERE id IN ({', '.join('?' * len(id_list))})"
            cursor.execute(query, id_list)
            db_connect.commit()
        else:
            await bot.send_message(message.chat.id, 'На данный момент обновлений нет')
    except:
        await message.answer('В базе еще нет постов для вас. Повторите попытку позже.')
    db_connect.close()


@dp.message_handler(Text(equals='Добавить чат/канал для поиска'), state=None)
async def add_channel(message: types.Message) -> None:
    await ClientStatesGroup.add_channels_state.set()
    await message.answer('Отправь ссылки на каналы через запятую',
                         reply_markup=get_change_keyboard())


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.add_channels_state)
async def load_channel_list(message: types.Message, state: FSMContext) -> None:
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    cursor.execute(f'SELECT channel_for_search FROM user_channels WHERE user_id == {message.chat.id}')
    existed_channels = cursor.fetchall()
    existed_channels = [elem[0] for elem in existed_channels]

    data = message.text.strip().replace(' ', '').split(',')
    added_list = ''
    for channel in data:
        if 'https://t.me/' in channel:
            channel = channel.replace('https://t.me/', '')

        if channel not in existed_channels:
            cursor.execute(
                f'''INSERT INTO user_channels (
                                                user_id, 
                                                channel_for_search)
                                            VALUES (
                                                '{message.chat.id}',
                                                '{channel}'
                                            );
                                                '''
            )
            added_list += channel + '\n'
            db_connect.commit()
    db_connect.close()
    await message.answer(f'В отслеживание добавлены следующие каналы:\n\n{added_list}',
                         reply_markup=get_main_keyboard())

    await state.finish()


@dp.message_handler(Text(equals='Добавить ключевые слова'), state=None)
async def add_keywords(message: types.Message) -> None:
    await ClientStatesGroup.add_keywords_state.set()
    await message.answer('Отправь ключевые слова для поиска через запятую',
                         reply_markup=get_change_keyboard())


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.add_keywords_state)
async def load_keywords(message: types.Message, state: FSMContext) -> None:
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    cursor.execute(f'SELECT text_for_search FROM user_keywords WHERE user_id == {message.chat.id}')
    existed_keywords = cursor.fetchall()
    existed_keywords = [elem[0] for elem in existed_keywords]

    data = message.text.strip().replace(' ', '').split(',')
    added_list = ''
    for keyword in data:
        if keyword not in existed_keywords:
            cursor.execute(
                f'''INSERT INTO user_keywords (
                                                user_id, 
                                                text_for_search)
                                            VALUES (
                                                '{message.chat.id}',
                                                '{keyword}'
                                            );
                                                '''
            )

            added_list += keyword + '\n'
            db_connect.commit()
    db_connect.close()
    await message.answer(f'В поиск добавлены следующие ключевые слова:\n\n{added_list}',
                         reply_markup=get_main_keyboard())

    await state.finish()


@dp.message_handler(Text(equals='Удалить чат/канал из поиска'))
async def remove_channel(message: types.Message) -> None:
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    cursor.execute(f'SELECT id, channel_for_search FROM user_channels WHERE user_id = {message.chat.id};')
    data = cursor.fetchall()

    answer_string = 'Что бы удалить каналы из отслеживания отправь мне их номера через запятую:\n\n'
    for index, channel in data:
        answer_string += f'{index}. {channel}\n'

    await ClientStatesGroup.remove_channel_state.set()
    await message.answer(answer_string, reply_markup=get_change_keyboard())


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.remove_channel_state)
async def remove_channels_from_db(message: types.Message, state: FSMContext):
    data = message.text.strip().replace(' ', '').split(',')

    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()
    try:
        cursor.execute(f"DELETE FROM user_channels WHERE id IN ({','.join(data)}) and user_id = {message.chat.id};")
        db_connect.commit()
        db_connect.close()
        await message.answer('Каналы удалены из отслеживания.', reply_markup=get_main_keyboard())
        await state.finish()
    except:
        await message.answer('Что-то пошло не так, повторите попытку.')


@dp.message_handler(Text(equals='Удалить ключевые слова'))
async def remove_keywords(message: types.Message) -> None:
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    cursor.execute(f'SELECT id, text_for_search FROM user_keywords WHERE user_id = {message.chat.id};')
    data = cursor.fetchall()

    answer_string = 'Что бы удалить ключевые слова из поиска отправь мне их номера через запятую:\n\n'
    for index, keyword in data:
        answer_string += f'{index}. {keyword}\n'

    await ClientStatesGroup.remove_keywords_state.set()
    await message.answer(answer_string, reply_markup=get_change_keyboard())


@dp.message_handler(lambda message: message.text, state=ClientStatesGroup.remove_keywords_state)
async def remove_keywords_from_db(message: types.Message, state: FSMContext):
    data = message.text.strip().replace(' ', '').split(',')

    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()
    try:
        cursor.execute(f"DELETE FROM user_keywords WHERE id IN ({','.join(data)}) and user_id = {message.chat.id};")
        db_connect.commit()
        db_connect.close()
        await message.answer('Ключевые слова удалены из отслеживания.', reply_markup=get_main_keyboard())
        await state.finish()

    except:
        await message.answer('Что-то пошло не так, повторите попытку.')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
