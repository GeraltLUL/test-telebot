import os
import pandas as pd
import telebot
from telebot import types

token = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(token, parse_mode='HTML')

file_db = 'db.csv'
df = None

def init_db():
    global df
    try:
        df = pd.read_csv(file_db, dtype={'id': int, 'user_id': int, 'plan': str})
    except:
        df = pd.DataFrame(columns=['id','user_id','plan'])

def save_db():
    global df
    df.to_csv(file_db, index=False)

def next_id():
    global df
    if not df.empty:
        return int(df['id'].max()) + 1
    else:
        return 1

def add_task(user_id, task):
    global df
    d = {'id': next_id(), 'user_id': int(user_id), 'plan': task}
    df = pd.concat([df, pd.DataFrame([d])], ignore_index=True)
    save_db()

def user_list_tasks(user_id):
    uid = int(user_id)
    res = df[df['user_id'] == uid]
    return res['plan'].tolist()

def remove_task(user_id, task):
    global df
    uid = int(user_id)
    matches = df[(df['user_id'] == uid) & (df['plan'] == task)]

    if matches.empty:
        return False

    f = matches.index[0]
    df = df.drop(f).reset_index(drop=True)
    save_db()
    return True

def remove_all_tasks(user_id):
    global df
    df = df[df['user_id'] != int(user_id)].reset_index(drop=True)
    save_db()

def count_tasks(user_id):
    uid = int(user_id)
    res = df[df['user_id'] == uid]
    return len(res)

def find_tasks(user_id, keyword):
    key = keyword.lower()
    tasks = user_list_tasks(user_id)
    res = []
    for t in tasks:
        if key in t.lower():
            res.append(t)
    return res

def main_keyboard(chat_id, text="Выберите действие"):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('Добавить дело', 'Показать список', 'Удалить дело', 'Удалить все дела', 'Найти', 'О боте')
    bot.send_message(chat_id, text, reply_markup=kb)

@bot.message_handler(commands=['start','help'])
def start_handler(m):
    init_db()
    bot.send_message(m.chat.id, f"Привет, {m.from_user.first_name}!")
    main_keyboard(m.chat.id, "Меню:")

@bot.message_handler(func=lambda m: m.text is not None)
def router(m):
    text = m.text.strip()
    if text == 'Добавить дело':
        msg = bot.send_message(m.chat.id, "Введите название задачи")
        bot.register_next_step_handler(msg, add_task_handler)
    elif text == 'Показать список':
        tasks = user_list_tasks(m.from_user.id)
        if tasks:
            formatted = []
            for i, t in enumerate(tasks, start=1):
                formatted.append(f"{i}) {t}")
            bot.send_message(m.chat.id, "\n".join(formatted))
        else:
            bot.send_message(m.chat.id, "Список пуст")
        main_keyboard(m.chat.id)
    elif text == 'Удалить дело':
        tasks = user_list_tasks(m.from_user.id)
        if not tasks:
            bot.send_message(m.chat.id, "Список дел пуст")
            main_keyboard(m.chat.id)
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        for t in tasks:
            kb.add(types.KeyboardButton(t))
        msg = bot.send_message(m.chat.id, "Выберите задачу для удаления", reply_markup=kb)
        bot.register_next_step_handler(msg, delete_one_handler)
    elif text == 'Удалить все дела':
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Да, удалить всё", callback_data="confirm_delete"))
        kb.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_delete"))
        bot.send_message(m.chat.id, "Удалить все задачи?", reply_markup=kb)
    elif text == 'Найти':
        msg = bot.send_message(m.chat.id, "Напишите ключевое слово для поиска")
        bot.register_next_step_handler(msg, find_handler)
    elif text == 'О боте':
      info = (
          "Это бот для ведения личного списка задач.\n"
          "Можно добавлять, смотреть, удалять задачи и искать задачи по определенному слову.\n"
          "Все задачи сохраняются локально, так что бот помнит ваш список!\n"
      )
      bot.send_message(m.chat.id, info)
      main_keyboard(m.chat.id)
    else:
        bot.send_message(m.chat.id, "Выберите кнопку из меню")
        main_keyboard(m.chat.id)

def add_task_handler(m):
    task = (m.text or "").strip()
    if task:
        add_task(m.from_user.id, task)
        bot.send_message(m.chat.id, "Задача успешно добавлена")
    else:
        bot.send_message(m.chat.id, "Введите название задачи")
    main_keyboard(m.chat.id)

def delete_one_handler(m):
    task = (m.text or "").strip()
    res = remove_task(m.from_user.id, task)

    if res:
        bot.send_message(m.chat.id, "Задача успешно удалена")
    else:
        bot.send_message(m.chat.id, "Задача не найдена")

    main_keyboard(m.chat.id)

def find_handler(m):
    task = (m.text or "").strip()
    if not task:
        bot.send_message(m.chat.id, "Пустой запрос")
        main_keyboard(m.chat.id)
        return

    matches = find_tasks(m.from_user.id, task)
    if matches:
        bot.send_message(m.chat.id, "\n".join(matches))
    else:
        bot.send_message(m.chat.id, "Совпадений не найдено")

    main_keyboard(m.chat.id)


@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    if c.data == 'confirm_delete':
        remove_all_tasks(c.from_user.id)
        try:
            bot.edit_message_text("Все задачи удалены", chat_id=c.message.chat.id, message_id=c.message.message_id)
        except:
            bot.send_message(c.message.chat.id, "Все задачи удалены")
        main_keyboard(c.message.chat.id)
        bot.answer_callback_query(c.id, "Удалено")
    elif c.data == 'cancel_delete':
        try:
            bot.edit_message_text("Удаление отменено", chat_id=c.message.chat.id, message_id=c.message.message_id)
        except:
            bot.send_message(c.message.chat.id, "Удаление отменено")
        main_keyboard(c.message.chat.id)
        bot.answer_callback_query(c.id, "Отмена")
    else:
        bot.answer_callback_query(c.id, "Неизвестно")

@bot.message_handler(content_types=['text'])
def fallback(m):
    main_keyboard(m.chat.id, "Выберите действие")

init_db()
bot.infinity_polling()