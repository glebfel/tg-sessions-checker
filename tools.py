import datetime
import json
import os
import pathlib
import python_socks
import telethon
import shutil
import credentials
from telethon import TelegramClient

DIR_PATH = str(pathlib.Path(__file__).parent)


def get_session_file_path(session: str) -> str:
    """
    get sessions file path
    :param session: phone number of the session (str)
    :return: absolute path to the session file
    """
    session_files_path = DIR_PATH + "/sessions"
    return f"{session_files_path}/{session}.session"


def clean_valid_folder():
    dst_path = DIR_PATH + '/valid_sessions/'
    if os.path.exists(dst_path):
        directory = os.fsencode(dst_path)
        for file in os.listdir(directory):
            os.remove(dst_path + file.decode("utf-8"))


def move_to_valid_folder(session):
    """
    move valid session file to the 'valid_sessions' folder with valid sessions files
    :param session:
    :return:
    """
    dst_path = DIR_PATH + '/valid_sessions'
    if not os.path.exists(dst_path):
        os.makedirs(dst_path)
    shutil.copy(get_session_file_path(session), dst_path)


def get_proxy() -> dict:
    """
    get proxy in TelegramClient format
    :return: dict with proxy settings
    """
    if not credentials.PROXY:
        return None
    proxy = credentials.PROXY.replace('http://', '').replace('@', ':')
    proxy_parts = proxy.split(':')
    return dict(proxy_type=python_socks.ProxyType.HTTP, addr=proxy_parts[2], port=int(proxy_parts[3]),
                username=proxy_parts[0], password=proxy_parts[1])


def create_report(valid_sessions: list, invalid_sessions: list):
    """
    create output report in report.json file
    """
    report_path = DIR_PATH + "/report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Report time: {datetime.datetime.now()}\n\n")
        if valid_sessions:
            f.write(f"Valid sessions:\n")
            for i in valid_sessions:
                f.write(i + "\n")
            f.write(f"\n")
        if invalid_sessions:
            f.write(f"Invalid sessions:\n")
            for i in invalid_sessions:
                f.write(i + "\n")


def get_2fa(session: str) -> str:
    """
    extract 2fa code from file (if exists) of given session
    :param session:
    :return:
    """
    # find json config file of given phone number
    path = DIR_PATH + f"/tg_sessions/{session}.json"
    if not os.path.isfile(path):
        print(f"Config file for {session} is absent!")
        return None
    with open(path, encoding='utf-8') as f:
        content = f.read()
    data = json.loads(content)
    return data['twoFA']


def get_all_sessions_from_dir() -> list:
    """
    return all sessions absolute paths
    :return: list of all all sessions absolute paths (list)
    """
    sessions = []
    if not os.path.exists(DIR_PATH + '/sessions'):
        print("'sessions' folder doesn't exists!")
        return None
    directory = os.fsencode(DIR_PATH + '/sessions')
    for file in os.listdir(directory):
        filename = str(os.fsdecode(file)).split('.')
        if 'session' == filename[1].strip():
            sessions.append(filename[0])
    if not sessions:
        print("'sessions' folder is empty!")
        return None
    return sessions


async def check():
    """check session"""

    clean_valid_folder()
    sessions = get_all_sessions_from_dir()
    if not sessions:
        return

    print(f"{len(sessions)} sessions were found!\n")

    valid_sessions = []
    invalid_sessions = []

    for ind, s in enumerate(sessions):

        # get tg client
        client = TelegramClient(get_session_file_path(s), credentials.API_ID,
                                credentials.API_HASH, timeout=10, proxy=get_proxy())

        try:
            await client.connect()
            if not await client.is_user_authorized():
                password = get_2fa(s)
                if password:
                    await client.sign_in(password=password)

            await client.get_entity("https://t.me/telegram")
            output = s + " is valid!\n"
            print(output)
            valid_sessions.append(s)
            move_to_valid_folder(s)
        except (telethon.errors.PhoneNumberBannedError,
                telethon.errors.rpcerrorlist.UserDeactivatedBanError,
                telethon.errors.rpcerrorlist.AuthKeyDuplicatedError,
                telethon.errors.rpcerrorlist.SessionRevokedError) as e:
            output = s + " is not valid!" + "\nReason: " + str(e) + "\n"
            print(output)
            invalid_sessions.append(s)
        except telethon.errors.FloodWaitError as e:
            output = s + " is valid!\n"
            print(output)
            valid_sessions.append(s)
            move_to_valid_folder(s)
        except telethon.errors.rpcerrorlist.HashInvalidError:
            print(e)
        finally:
            print(f"{ind + 1}/{len(sessions)} sessions checked!\n")
            await client.disconnect()

    create_report(valid_sessions, invalid_sessions)