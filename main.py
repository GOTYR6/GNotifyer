from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from urllib3.exceptions import ProtocolError, MaxRetryError
from threading import Thread, Event
from configuration import config
from tqdm import tqdm
import time
from datetime import datetime as dt
import telebot
from telebot import types
import requests
import os
import atexit
from random import randrange
import tempfile
from PIL import ImageGrab

event = Event()
event.set()
bot = telebot.TeleBot(config.TOKEN)


def get_chat_id():
    url = f"https://api.telegram.org/bot{config.TOKEN}/getUpdates"
    print(requests.get(url).json())


def get_diver():
    options = webdriver.ChromeOptions()
    options.add_argument('--allow-profiles-outside-user-dir')
    options.add_argument('--enable-profile-shortcut-manager')
    options.add_argument(r'user-data-dir=C:/User')
    options.add_argument('--profile-directory=Profile 1')
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.minimize_window()
    wait = WebDriverWait(driver, config.DRIVER_TIMEOUT)
    return driver, wait


def get_authorized(driver, wait):
    while True:
        try:
            driver.get(config.AUTH_PAGE)
            wait.until(ec.visibility_of_element_located((By.XPATH, config.EMAIL_FIELD)))
            email = driver.find_element(By.XPATH, config.EMAIL_FIELD)
            password = driver.find_element(By.XPATH, config.PASSWORD_FIELD)
            email.send_keys(config.LOGIN)
            password.send_keys(config.PASSWORD)
            login_button = driver.find_element(By.XPATH, config.LOGIN_BUTTON)
            login_button.click()
            wait.until(ec.visibility_of_element_located((By.CLASS_NAME, config.ITEM_TO_WAIT)))
            break
        except (TimeoutException, NoSuchElementException):
            if ec.visibility_of_element_located((By.CLASS_NAME, config.ITEM_TO_WAIT)):
                break
            else:
                continue


def get_tasks_page(driver, wait, offset=0):
    while True:
        try:
            driver.get(config.TASKS_PAGE.format(offset))
            wait.until(ec.visibility_of_all_elements_located((By.CLASS_NAME, config.TASKS_ROWS)))
            break
        except (TimeoutException, NoSuchElementException):
            if ec.visibility_of_element_located((By.XPATH, config.EMAIL_FIELD)):
                get_authorized(driver, wait)
                continue


def get_task_data(task) -> dict:
    task_data, deadline = dict(), dict()

    def get_id():
        task_data.setdefault('id', task.find_element(By.CLASS_NAME, config.TASK_ID).text)

    def get_link():
        task_data.setdefault('link', task.find_element(By.CLASS_NAME, config.TASK_LINK).get_attribute('href'))

    def get_date():
        deadline.setdefault('date', task.find_element(By.CLASS_NAME, config.TASK_DEADLINE_DATE).text)

    def get_time():
        deadline.setdefault('time', task.find_element(By.CLASS_NAME, config.TASK_DEADLINE_TIME).text)

    t_get_id = Thread(target=get_id)
    t_get_link = Thread(target=get_link)
    t_get_date = Thread(target=get_date())
    t_get_time = Thread(target=get_time())
    t_get_id.start(), t_get_link.start(), t_get_date.start(), t_get_time.start()
    t_get_id.join(), t_get_link.join(), t_get_date.join(), t_get_time.join()
    task_data.setdefault('deadline', ' '.join((deadline.get('date'), deadline.get('time'))))
    return task_data


def get_tasks(exist_tasks_id, driver, wait):
    tasks_data = dict()
    get_tasks_page(driver, wait)
    tasks_quantity = int(driver.find_element(By.CLASS_NAME, config.TASKS_QUANTITY).text.split()[0])
    for offset in range(0, tasks_quantity, 100):
        if offset != 0:
            get_tasks_page(driver, wait, offset)
        tasks = driver.find_elements(By.CLASS_NAME, config.TASKS_ROWS)
        cur_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        for task in tqdm(tasks, desc=f'Parsing was started at {cur_time}', unit=' task'):
            task_data: dict = get_task_data(task)
            tasks_data.setdefault(task_data.get('id'), task_data)
    if exist_tasks_id:
        parsed_tasks_id = {task_id for task_id in tasks_data}
        new_tasks_id = parsed_tasks_id.difference(exist_tasks_id)
        if new_tasks_id:
            new_tasks_data = sorted([tasks_data.get(task_id) for task_id in new_tasks_id],
                                    key=lambda new_task: dt.strptime(new_task.get('deadline'), "%d.%m.%Y %H:%M"))
            return parsed_tasks_id, new_tasks_data
        else:
            return parsed_tasks_id, None
    else:
        parsed_tasks_id = {task_id for task_id in tasks_data}
        return parsed_tasks_id, None


def start_notifyer(timeout: int):
    exist_tasks_id = set()
    remind_time = time.time()
    driver, wait = get_diver()
    bot.send_message(chat_id=config.CHAT_ID,
                     text='Notifyer is running, you will be notified about new tasks asap👍')
    while not event.is_set():
        try:
            exist_tasks_id, new_tasks = get_tasks(exist_tasks_id, driver, wait)
            if new_tasks:
                print(f'Founded {len(new_tasks)} tasks')
                message = f'Количество новых задач: {len(new_tasks)}\n'
                for index, task in enumerate(new_tasks, start=1):
                    message += f"{index}) [{task.get('id')}]({task.get('link')}) Крайний срок: {task.get('deadline')}\n"
                bot.send_message(chat_id=config.CHAT_ID, text=message, parse_mode='Markdown')
            if time.time() - remind_time > config.REMIND_TIMEOUT and not event.is_set():
                bot.send_message(chat_id=config.CHAT_ID, text='Notifyer is still in progress!')
                remind_time = time.time()
            event.wait(timeout + randrange(timeout))
        except KeyboardInterrupt:
            print('Parsing has been stopped')
        except (ProtocolError, MaxRetryError):
            break
        except (Exception,):
            continue
    driver.quit()
    bot.send_message(chat_id=config.CHAT_ID, text='Notifyer has been stopped⛔️')


@bot.message_handler(commands=['start'])
def welcome(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    startup = types.KeyboardButton('Start notifyer')
    shutdown = types.KeyboardButton('Shut down notifyer')
    screen = types.KeyboardButton('Take screenshot')
    turnoff = types.KeyboardButton('Turn off PC')
    markup.add(startup, shutdown, screen, turnoff)
    bot.send_message(message.chat.id, 'Welcome! How can I help you?👋', reply_markup=markup)


@bot.message_handler(regexp='Start notifyer')
def remote_startup(message: types.Message):
    if event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        event.clear()
        config.CHAT_ID = message.chat.id
        return start_notifyer(timeout=config.NOTIFYER_TIMEOUT)
    if not event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return bot.send_message(message.chat.id, 'Notifyer is already running!👌')


@bot.message_handler(regexp='Shut down notifyer')
def remote_shutdown(message: types.Message):
    if not event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return event.set()
    if event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return bot.send_message(message.chat.id, 'Notifyer is already has been stopped!✋')


@bot.message_handler(regexp='Take screenshot')
def screenshot(message: types.Message):
    if message.chat.id in config.ALLOW_CHAT_ID:
        path = tempfile.gettempdir() + 'screenshot.png'
        ImageGrab.grab().save(path, 'PNG')
        return bot.send_document(message.chat.id, open(path, 'rb'))


@bot.message_handler(regexp='Turn off PC')
def confirm_turnoff(message: types.Message):
    if message.chat.id in config.ALLOW_CHAT_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm = types.InlineKeyboardButton('Yes', callback_data='confirm')
        decline = types.InlineKeyboardButton('No', callback_data='decline')
        markup.add(confirm, decline)
        if event.is_set():
            return bot.send_message(message.chat.id, 'Are you sure you want to turn off your PC?', reply_markup=markup)
        if not event.is_set():
            return bot.send_message(message.chat.id,
                                    'Warning! Notifyer is still in progress, do you still want to turn off your PC?',
                                    reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_inline(call):
    try:
        if call.message:
            if call.data == 'confirm':
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Turning off your PC🖥🔌', reply_markup=None)
                return os.system("shutdown -s -t 0")
            if call.data == 'decline':
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                return bot.answer_callback_query(call.id, 'You canceled the PC shutdown❌')
    except Exception as e:
        print(e)


@atexit.register
def stop_notifyer():
    if os.path.isfile(config.IO_FILE):
        os.remove(config.IO_FILE)


if __name__ == "__main__":
    bot.infinity_polling()
    # start_notifyer(config.INTERVAL)
