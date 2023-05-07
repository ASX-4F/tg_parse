import sqlite3
from pyrogram import Client
from datetime import date
from datetime import timedelta

api_id = 1611714
api_hash = '5c8a7780d6425c49d2e201d352839b99'

app = Client("my_account", api_id=api_id, api_hash=api_hash)


def make_search():
    # # Открываем файл с настройками
    # with open('settings.json', 'r', encoding='utf-8') as file:
    #     settings_dict = json.load(file)

    # Подключаемся к ДБ
    db_connect = sqlite3.connect('database/tg_parse.db')
    cursor = db_connect.cursor()

    # Читаем список каналов, юзеров и ключевых слов
    cursor.execute('SELECT uc.user_id, uc.channel_for_search, uk.text_for_search FROM user_channels uc JOIN user_keywords uk ON uc.user_id = uk.user_id')

    search_data = {}
    for row in cursor.fetchall():
        user_id = row[0]
        channel = row[1]
        keyword = row[2]

        if user_id not in search_data:
            search_data[user_id] = {
                'channels': set(),
                'keywords': set()
            }
        search_data[user_id]['channels'].add(channel)
        search_data[user_id]['keywords'].add(keyword)

    # Удаляем записи старше 3 дней
    three_days_ago = date.today() - timedelta(days=3)

    query = f"DELETE FROM search_results WHERE message_date < '{three_days_ago.strftime('%Y-%m-%d')}';"
    cursor.execute(query)
    db_connect.commit()

    # Получаем список записей из бд, что бы класть в нее только уникальные
    cursor.execute('SELECT message_text from search_results')
    data = cursor.fetchall()

    old_messages = [elem[0] for elem in data]


    app.start()
    for user in search_data:
        for channel in search_data[user]['channels']:
            for word in search_data[user]['keywords']:
                try:
                    for message in app.search_messages(chat_id=channel, query=word, limit=20):
                        if message.date.date() == date.today() and message.text not in old_messages and '#помогу' not in message.text.lower():
                            match message.from_user:
                                case None:
                                    cursor.execute(
                                        f'''INSERT INTO search_results (
                                            search_user, 
                                            message_date, 
                                            message_from_user, 
                                            message_text,
                                            message_url,
                                            is_frozen)
                                        VALUES (
                                            '{user}',
                                            '{message.date.date().strftime('%Y-%m-%d')}',
                                            '{message.chat.username}',
                                            '{message.text}',
                                            '{message.link}',
                                            False
                                        );
                                            '''

                                    )
                                case _:
                                    cursor.execute(
                                        f'''INSERT INTO search_results (
                                            search_user, 
                                            message_date, 
                                            message_from_user, 
                                            message_text,
                                            message_url,
                                            is_frozen)
                                        VALUES (
                                            '{user}',
                                            '{message.date.date().strftime('%Y-%m-%d')}',
                                            '{message.from_user.username}',
                                            '{message.text}',
                                            '{message.link}',
                                            False
                                            );
                                            '''
                                    )

                            db_connect.commit()
                except: continue
    db_connect.close()
    app.stop()


if __name__ == '__main__':
    make_search()
