import argparse
import asyncio
import logging

import aiofiles
from datetime import datetime

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
    parser.add_argument(
        '--history', default='minechat.history',
    )
    args = parser.parse_args()
    return args


async def connect_to_chat(host, port, history_filepath):
    reader, writer = await asyncio.open_connection(host, port)
    messages = 1000
    while messages:
        line = await reader.readline()
        msg = line.decode()
        date = datetime.now().strftime('%d.%m.%y %H:%M')
        full_msg = f'[{date}] {msg}'
        async with aiofiles.open(history_filepath, 'a') as file:
            await file.write(full_msg)
        print(full_msg.strip())
        messages -= 1
    logger.info('Close the connection')
    writer.close()


if __name__ == '__main__':
    args = parse_args()
    logger.info('Start server loop')
    try:
        asyncio.run(connect_to_chat(args.host, args.port, args.history))
    except KeyboardInterrupt:
        logger.info('Exiting')
