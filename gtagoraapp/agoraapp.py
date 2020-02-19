import argparse
import sys
from getpass import getpass

from gtagoraapp.details.app import App
from gtagoraapp.details.settings import Settings

def get_input(text, existing_value=None, has_default=False):
    if existing_value:
        return f'{text} [ENTER={existing_value}]: '
    elif has_default:
        return f'{text} [ENTER=default]: '
    else:
        return f'{text}: '


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    args = parser.parse_args()

    if args.setup:
        settings = Settings()
        server = input(get_input('agora server', settings.server))
        server = server.strip() if server else settings.server
        username = input(get_input('username'))
        password = getpass()
        download_path = input(get_input('download path', settings.download_path))
        download_path = download_path.strip() if download_path else settings.download_path
        logfile = input(get_input('logfile path', settings.logfile, True))
        logfile = logfile.strip() if logfile else settings.logfile
        log_level = input(get_input('log level', settings.log_level, True))
        log_level = log_level.upper() if log_level else settings.log_level
        console_log_level = None
        if query_yes_no('do console logging?'):
            console_log_level = input(get_input('console log level', settings.console_log_level, True))
            console_log_level = console_log_level.upper() if console_log_level else settings.console_log_level

        session_key = App.get_session_key(server, username, password)
        settings.setup(server, download_path, session_key, logfile, log_level, console_log_level)
        exit(0)

    app = App()
    app.run()
