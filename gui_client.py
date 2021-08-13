import argparse
import asyncio
import json
import logging
from datetime import datetime

import aiofiles

import gui

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


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
    async with aiofiles.open('.credentials') as file:
        content = await file.read()
        if content:
            return json.loads(content)
        return None


def load_messages(msg_queue):
    with open('minechat.history') as file:
        for line in file.read().splitlines():
            msg_queue.put_nowait(line)


async def save_messages(history_queue):
    while True:
        msg = await history_queue.get()
        async with aiofiles.open('minechat.history', 'a') as file:
            await file.write(msg)


async def read_messages(host, port, msg_queue, history_queue, status_updates_queue):
    reader, writer = await asyncio.open_connection(host, port)
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
    try:
        while True:
            line = await reader.readline()
            msg = line.decode()
            date = datetime.now().strftime('%d.%m.%y %H:%M')
            full_msg = f'[{date}] {msg}'
            msg_queue.put_nowait(full_msg.strip())
            history_queue.put_nowait(full_msg)
    finally:
        logger.info('Close the connection')
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


async def send_msgs(host, port, snd_queue, status_updates_queue):
    reader, writer = await asyncio.open_connection(host, port)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
    credentials = await load_credentials()
    logger.debug('credentials: %s', credentials)
    welcome_msg = await reader.readline()
    logger.debug('Welcome message: %s', welcome_msg)
    writer.write((credentials['account_hash'] + '\n').encode())
    response = await reader.readline()
    nickname = json.loads(response.decode())['nickname']
    event = gui.NicknameReceived(nickname)
    status_updates_queue.put_nowait(event)
    logger.debug('Response: %s', response)
    await writer.drain()
    try:
        while True:
            msg = await snd_queue.get()
            logger.debug('message: %s', msg)
            writer.write((msg + '\n\n').encode())
            await writer.drain()
    finally:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


async def main(messages_queue, sending_queue, status_updates_queue, history_queue):
    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_messages('minechat.dvmn.org', 5000, messages_queue, history_queue, status_updates_queue),
        save_messages(history_queue),
        send_msgs('minechat.dvmn.org', 5050, sending_queue, status_updates_queue),
    )


if __name__ == '__main__':
    args = parse_args()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    history_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    load_messages(messages_queue)
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    loop.run_until_complete(
        main(messages_queue, sending_queue, status_updates_queue, history_queue),
    )
