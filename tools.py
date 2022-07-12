import datetime
import json
import os
import pathlib
import python_socks
import telethon
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


def get_proxy() -> dict:
    """
    get proxy in TelegramClient format
    :return: dict with proxy settings
    """
    proxy = credentials.PROXY.replace('http://', '').replace('@', ':')
    proxy_parts = proxy.split(':')
    return dict(proxy_type=python_socks.ProxyType.HTTP, addr=proxy_parts[2], port=int(proxy_parts[3]),
                username=proxy_parts[0], password=proxy_parts[1])


def create_report():
    """
    create output report in report.json file
    :return:
    """
    report_path = DIR_PATH + "/report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Start time: {datetime.datetime.now()}\n")


def add_to_report(string):
    """
    add info about phone in report.json file
    :return:
    """
    report_path = DIR_PATH + "/report.json"

    with open(report_path, "a+", encoding="utf-8") as f:
        f.write(f"{string}\n")


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
    create_report()
    sessions = get_all_sessions_from_dir()
    if not sessions:
        return

    print(f"{len(sessions)} sessions were found!")

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
                else:
                    output = s + " is not valid!" + "\nReason: 2fa code is required\n\n"
                    print(output)
                    add_to_report(output)
                    continue

            a = await client.get_entity("https://t.me/telegram")
            output = s + " is valid!\n\n"
            print(output)
            add_to_report(output)
        except (telethon.errors.PhoneNumberBannedError,
                telethon.errors.rpcerrorlist.UserDeactivatedBanError,
                telethon.errors.rpcerrorlist.AuthKeyDuplicatedError,
                telethon.errors.rpcerrorlist.SessionRevokedError) as e:
            output = s + " is not valid!" + "\nReason:" + str(e) + "\n\n"
            print(output)
            add_to_report(output)
        except telethon.errors.FloodWaitError as e:
            output = s + " is valid!\n\n"
            print(output)
            add_to_report(output)
        except telethon.errors.rpcerrorlist.HashInvalidError:
            print(e)
        finally:
            print(f"{ind + 1}/{len(sessions)} sessions checked!")
            await client.disconnect()
