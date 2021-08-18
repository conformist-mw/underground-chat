import json
import logging
import os
from tkinter import messagebox

import aiofiles

from exceptions import InvalidToken, TokenDoesNotExists
from gui import NicknameReceived

logger = logging.getLogger(__file__)


async def load_credentials():
    if not os.path.exists('.credentials'):
        messagebox.showerror(
            'Credentials not found',
            'File .credentials does not exists. Please register first',
        )
        raise TokenDoesNotExists
    async with aiofiles.open('.credentials') as file:
        content = await file.read()
        if content:
            return json.loads(content)
        return None


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
