import asyncio
import logging
from contextlib import suppress
from datetime import datetime

import aiofiles
from async_timeout import timeout

import gui
from gui import ReadConnectionStateChanged, SendingConnectionStateChanged

from .auth import authorize
from .utils import ConnectionNotify, open_connection

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
watchdog_logger = logging.getLogger('watchdog')
watchdog_logger.setLevel(logging.DEBUG)


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


async def watch_for_connection(watchdog_queue):
    while True:
        try:
            async with timeout(2):
                msg = await watchdog_queue.get()
                watchdog_logger.debug(msg)
        except asyncio.TimeoutError:
            raise ConnectionError


async def main(queues):
    await asyncio.gather(
        watch_for_connection(queues['watchdog']),
        load_messages(queues['msgs']),
        gui.draw(queues['msgs'], queues['send'], queues['status']),
        read_messages('minechat.dvmn.org', 5000, queues),
        save_messages(queues),
        send_msgs('minechat.dvmn.org', 5050, queues),
    )


if __name__ == '__main__':
    queue_names = {'msgs', 'send', 'status', 'history', 'watchdog'}
    queues = {name: asyncio.Queue() for name in queue_names}
    loop = asyncio.get_event_loop()
    with suppress(gui.TkAppClosed):
        loop.run_until_complete(main(queues))
