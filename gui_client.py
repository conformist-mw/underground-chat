import argparse
import asyncio
import logging
from datetime import datetime

import gui

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host', default='minechat.dvmn.org',
    )
    parser.add_argument(
        '--port', default=5000,
    )
    return parser.parse_args()


async def read_messages(host, port, msg_queue):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        while True:
            line = await reader.readline()
            msg = line.decode()
            date = datetime.now().strftime('%d.%m.%y %H:%M')
            full_msg = f'[{date}] {msg}'
            msg_queue.put_nowait(full_msg.strip())
    finally:
        logger.info('Close the connection')
        writer.close()


async def main(messages_queue, sending_queue, status_updates_queue):
    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_messages('minechat.dvmn.org', 5000, messages_queue)
    )


if __name__ == '__main__':
    args = parse_args()
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(messages_queue, sending_queue, status_updates_queue),
    )
