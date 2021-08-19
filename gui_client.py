import asyncio
import configparser
import logging
from contextlib import suppress
from datetime import datetime

import aiofiles
import anyio
from anyio import sleep
from async_timeout import timeout

import gui
from auth import authorize
from gui import ReadConnectionStateChanged, SendingConnectionStateChanged
from utils import ConnectionNotify, open_connection, reconnect

WATCHDOG_TIMEOUT = 5

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
watchdog_logger = logging.getLogger('watchdog')
watchdog_logger.setLevel(logging.DEBUG)


async def load_messages(msg_queue, filename):
    async with aiofiles.open(filename) as file:
        async for line in file:
            msg_queue.put_nowait(line.rstrip())


async def save_messages(queue, filename):
    while True:
        msg = await queue.get()
        async with aiofiles.open(filename, 'a') as file:
            await file.write(msg)


async def read_messages(host, port, queues):
    notify = ConnectionNotify(queues['status'], ReadConnectionStateChanged)
    async with open_connection(host, port, notify) as (reader, writer):
        while True:
            line = await reader.readline()
            msg = line.decode()
            date = datetime.now().strftime('%d.%m.%y %H:%M')
            full_msg = f'[{date}] {msg}'
            queues['msgs'].put_nowait(full_msg.strip())
            queues['history'].put_nowait(full_msg)
            queues['watchdog'].put_nowait('New message in chat')


async def send_msgs(host, port, queues):
    notify = ConnectionNotify(queues['status'], SendingConnectionStateChanged)
    async with open_connection(host, port, notify) as (reader, writer):
        await authorize(reader, writer, queues)
        while True:
            msg = await queues['send'].get()
            logger.debug('message: %s', msg)
            writer.write((msg + '\n\n').encode())
            await writer.drain()
            queues['watchdog'].put_nowait('Message sent')


async def ping_server(host, port, queues):
    notify = ConnectionNotify(queues['status'])
    async with open_connection(host, port, notify) as (reader, writer):
        while True:
            writer.write(b'\n')
            await writer.drain()
            await reader.readline()
            queues['watchdog'].put_nowait('Connection alive')
            await sleep(WATCHDOG_TIMEOUT)


async def watch_for_connection(watchdog_queue):
    while True:
        try:
            async with timeout(WATCHDOG_TIMEOUT):
                msg = await watchdog_queue.get()
                watchdog_logger.debug(msg)
        except asyncio.TimeoutError:
            raise ConnectionError


@reconnect
async def handle_connection(queues, settings):
    host = settings['reader']['host']
    reading_port = settings['reader']['port']
    sending_port = settings['writer']['port']
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(watch_for_connection, queues['watchdog'])
        task_group.start_soon(read_messages, host, reading_port, queues)
        task_group.start_soon(send_msgs, host, sending_port, queues)
        task_group.start_soon(ping_server, host, sending_port, queues)


async def main(queues, settings):
    history_filename = settings['common']['history_filename']
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(load_messages, queues['msgs'], history_filename)
        task_group.start_soon(
            gui.draw, queues['msgs'], queues['send'], queues['status'],
        )
        task_group.start_soon(
            save_messages, queues['history'], history_filename,
        )
        task_group.start_soon(handle_connection, queues, settings)


if __name__ == '__main__':
    settings = configparser.ConfigParser()
    settings.read('settings.ini')
    queue_names = {'msgs', 'send', 'status', 'history', 'watchdog'}
    queues = {name: asyncio.Queue() for name in queue_names}
    loop = asyncio.get_event_loop()
    with suppress(gui.TkAppClosed):
        loop.run_until_complete(main(queues, settings))
