import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from tkinter import messagebox
from contextlib import suppress

import aiofiles

import gui

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


class TokenDoesNotExists(Exception):
    ...


class InvalidToken(Exception):
    ...


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host', default='minechat.dvmn.org',
    )
    parser.add_argument(
        '--port', default=5000,
    )
    return parser.parse_args()


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


async def load_messages(msg_queue):
    async with aiofiles.open('minechat.history') as file:
        async for line in file:
            msg_queue.put_nowait(line.rstrip())


async def save_messages(queues):
    while True:
        msg = await queues['history'].get()
        async with aiofiles.open('minechat.history', 'a') as file:
            await file.write(msg)


async def read_messages(host, port, queues):
    queues['status'].put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host, port)
    queues['status'].put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
    try:
        while True:
            line = await reader.readline()
            msg = line.decode()
            date = datetime.now().strftime('%d.%m.%y %H:%M')
            full_msg = f'[{date}] {msg}'
            queues['msgs'].put_nowait(full_msg.strip())
            queues['history'].put_nowait(full_msg)
    finally:
        logger.info('Close the connection')
        queues['status'].put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        writer.close()
        if not writer.is_closing():
            await writer.wait_closed()


async def authorize(reader, writer):
    credentials = await load_credentials()
    logger.debug('credentials: %s', credentials)
    welcome_msg = await reader.readline()
    logger.debug('Welcome message: %s', welcome_msg)
    writer.write((credentials['account_hash'] + '\n').encode())
    await writer.drain()
    encoded_response = await reader.readline()
    response = json.loads(encoded_response.decode())
    if response is None:
        raise InvalidToken
    return response


async def send_msgs(host, port, queues):
    queues['status'].put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host, port)
    queues['status'].put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
    try:
        response = await authorize(reader, writer)
    except InvalidToken:
        messagebox.showerror(
            'Invalid Token', 'Check your token or register again',
        )
        raise
    nickname = response['nickname']
    event = gui.NicknameReceived(nickname)
    queues['status'].put_nowait(event)
    logger.debug('Response: %s', response)
    try:
        while True:
            msg = await queues['send'].get()
            logger.debug('message: %s', msg)
            writer.write((msg + '\n\n').encode())
            await writer.drain()
    finally:
        queues['status'].put_nowait(
            gui.SendingConnectionStateChanged.CLOSED,
        )
        writer.close()
        if not writer.is_closing():
            await writer.wait_closed()


async def main(queues):
    await asyncio.gather(
        load_messages(queues['msgs']),
        gui.draw(queues['msgs'], queues['send'], queues['status']),
        read_messages('minechat.dvmn.org', 5000, queues),
        save_messages(queues),
        send_msgs('minechat.dvmn.org', 5050, queues),
    )


if __name__ == '__main__':
    args = parse_args()
    queue_names = {'msgs', 'send', 'status', 'history', 'watchdog'}
    queues = {name: asyncio.Queue() for name in queue_names}
    loop = asyncio.get_event_loop()
    with suppress(InvalidToken, gui.TkAppClosed):
        loop.run_until_complete(main(queues))
