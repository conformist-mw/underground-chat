import asyncio
import json
import logging
from tkinter import messagebox

import aiofiles

from exceptions import InvalidToken
from gui import NicknameReceived

CREDENTIALS_FILENAME = '.credentials'

logger = logging.getLogger(__file__)


async def save_credentials(credentials):
    async with aiofiles.open(CREDENTIALS_FILENAME, 'w') as file:
        await file.write(json.dumps(credentials))


async def load_credentials():
    try:
        async with aiofiles.open(CREDENTIALS_FILENAME) as file:
            content = await file.read()
            return json.loads(content)
    except FileNotFoundError:
        logger.debug('Credentials file does not exists')
        pass
    except json.JSONDecodeError:
        logger.debug('Credentials file is empty or has invalid json')
        return {}


async def register(host, port, nickname):
    reader, writer = await asyncio.open_connection(host, port)
    msg = await reader.readline()
    logger.debug('Welcome message: %s', msg)
    writer.write(b'\n')
    await writer.drain()
    msg = await reader.readline()
    logger.debug('Second message: %s', msg)
    writer.write(f'{nickname or "Anonymous"}\n'.encode())
    await writer.drain()
    response = await reader.readline()
    logger.debug('Response credentials: %s', response)
    credentials = json.loads(response.decode())
    return credentials


async def authorize(reader, writer, queues):
    credentials = await load_credentials()
    logger.debug('credentials: %s', credentials)
    welcome_msg = await reader.readline()
    logger.debug('Welcome message: %s', welcome_msg)
    writer.write((credentials['account_hash'] + '\n').encode())
    await writer.drain()
    encoded_response = await reader.readline()
    response = json.loads(encoded_response.decode())
    if response is None:
        messagebox.showerror(
            'Invalid Token', 'Check your token or register again',
        )
        raise InvalidToken
    queues['status'].put_nowait(NicknameReceived(response['nickname']))
    logger.debug('Response: %s', response)
