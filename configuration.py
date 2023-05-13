import json


class Config:
    def __init__(self, default_config):
        try:
            with open(default_config) as f:
                default_config = json.load(f)
            self.LOGIN = default_config['LOGIN']
            self.PASSWORD = default_config['PASSWORD']
            self.AUTH_PAGE = default_config['AUTH_PAGE']
            self.TASKS_PAGE = default_config['TASKS_PAGE']
            self.NOTIFYER_TIMEOUT = default_config['NOTIFYER_TIMEOUT']
            self.DRIVER_TIMEOUT = default_config['DRIVER_TIMEOUT']
            self.REMIND_TIMEOUT = default_config['REMIND_TIMEOUT']
            self.IO_FILE = default_config['IO_FILE']
            self.TOKEN = default_config['TOKEN']
            self.ALLOW_CHAT_ID = default_config['ALLOW_CHAT_ID']
            self.CHAT_ID = default_config['CHAT_ID']
            self.EMAIL_FIELD = default_config['AUTH_ELEMENTS']['EMAIL_FIELD']
            self.PASSWORD_FIELD = default_config['AUTH_ELEMENTS']['PASSWORD_FIELD']
            self.LOGIN_BUTTON = default_config['AUTH_ELEMENTS']['LOGIN_BUTTON']
            self.ITEM_TO_WAIT = default_config['AUTH_ELEMENTS']['ITEM_TO_WAIT']
            self.TASKS_ROWS = default_config['TASKS_ELEMENTS']['TASKS_ROWS']
            self.TASKS_QUANTITY = default_config['TASKS_ELEMENTS']['TASKS_QUANTITY']
            self.TASK_ID = default_config['TASKS_ELEMENTS']['TASK_ID']
            self.TASK_LINK = default_config['TASKS_ELEMENTS']['TASK_LINK']
            self.TASK_DEADLINE_DATE = default_config['TASKS_ELEMENTS']['TASK_DEADLINE_DATE']
            self.TASK_DEADLINE_TIME = default_config['TASKS_ELEMENTS']['TASK_DEADLINE_TIME']
        except FileNotFoundError:
            raise Exception('Config file config/default_config.json is missing')

    def update_config(self, local_config):
        try:
            with open(local_config, 'r') as f:
                local_config = json.load(f)
            [list(map(lambda key: setattr(self, key, value.get(key)), value)) if isinstance(value, dict)
             else setattr(self, key, value) for key, value in local_config.items()]
        except FileNotFoundError:
            print('Updating config file config/local_config.json is missing')


config = Config('config/default_config.json')
config.update_config('config/local_config.json')
