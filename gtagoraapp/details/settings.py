import json
import logging
import os
from uuid import uuid4

from pathlib import PurePath, Path


class Settings:
    def __init__(self):
        json = self._get()
        self.server = json['server'] if 'server' in json else None
        self.download_path = json['download_path'] if 'download_path' in json else None
        self.session_key = json['session_key'] if 'session_key' in json else None
        self.app_id = json['app_id'] if 'app_id' in json else None
        self.logfile = json['logfile'] if 'logfile' in json else None
        self.log_level = json['log_level'] if 'log_level' in json else None
        self.console_log_level = json['console_log_level'] if 'console_log_level' in json else None

    def save(self):
        settings_file = self._get_or_create_file()
        with open(settings_file, 'w') as json_file:
            return json.dump(self.__dict__, json_file, indent=4)

    def setup(self, server, download_path, session_key, logfile=None, log_level=None, console_log_level=None):
        self.server = server
        self.download_path = Path(download_path).as_posix()
        self.session_key = session_key

        if not logfile:
            logfile = Path(self._get_dir(), 'gtagora-app-py.log')
        else:
            logfile = Path(logfile)
        self.logfile = str(logfile.as_posix())

        if not log_level:
            log_level = 'INFO'

        if not log_level in logging._nameToLevel:
            raise ValueError(f'Invalid log level. Possible levels are: CRITICAL, ERROR, WARNING, INFO, DEBUG')
        self.log_level = log_level

        if not console_log_level:
            console_log_level = 'INFO'

        if not console_log_level in logging._nameToLevel:
            raise ValueError(f'Invalid log level. Possible levels are: CRITICAL, ERROR, WARNING, INFO, DEBUG')
        self.console_log_level = console_log_level

        if not self.app_id:
            self.generate_app_id()
        self.save()

    def is_complete(self):
        for attr, value in self.__dict__.items():
            if value is None:
                return False

        return True


    def generate_app_id(self):
        self.app_id = str(uuid4())

    @staticmethod
    def get_path():
        return os.path.join(Settings._get_dir(), 'gt-agora-app-py.json')

    def _get(self):
        settings_file = self._get_or_create_file()
        with open(settings_file) as json_file:
            return json.load(json_file)

    def _get_or_create_file(self):
        if not os.path.exists(self._get_dir()):
            os.makedirs(self._get_dir(), exist_ok=True)

        if not os.path.exists(self.get_path()):
            with open(self.get_path(), "w") as file:
                file.write('{}')

        if not os.path.exists(self.get_path()):
            raise PermissionError('Cannot create the settings file')

        return self.get_path()

    @staticmethod
    def _get_dir():
        return os.path.expanduser('~') + '/.gyrotools/'
