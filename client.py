import argparse
import asyncio
import logging
import json
from asyncio import StreamReader, StreamWriter
from typing import Optional

import aiofiles

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--msg', required=True)
    parser.add_argument(
        '--host', default='minechat.dvmn.org',
    )
    parser.add_argument(
        '--port', default=5050,
    )
    parser.add_argument('--nickname')
    parser.add_argument('--verbose', '-v', action='count', default=1)
    args = parser.parse_args()
    return args


async def send(writer: StreamWriter, msg: str) -> None:
    writer.write((msg + '\n\n').encode())
    await writer.drain()


async def load_credentials():
    async with aiofiles.open('.credentials') as file:
        content = await file.read()
        if content:
            return json.loads(content)
        return None


async def register(
        reader: StreamReader,
        writer: StreamWriter,
        nickname: Optional[str],
) -> None:
    await send(writer, '\n')
    await send(writer, nickname or '')
    credentials = await reader.readline()
    logger.debug('Response credentials: %s', credentials)
    async with aiofiles.open('.credentials', 'w') as file:
        await file.write(credentials.decode().strip())


async def login(reader: StreamReader, writer: StreamWriter) -> None:
    logger.debug('Entering login')
    credentials = await load_credentials()
    logger.debug('Credentials: %s', credentials)
    await send(writer, credentials['account_hash'])
    response = await reader.readline()
    logger.debug('Response: %s', response)
    if json.loads(response.strip()) is None:
        raise ValueError('Incorrect account_hash.')


async def write_to_chat(
        host: str, port: int, msg: str, nickname: Optional[str],
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    welcome_msg = await reader.readline()
    logger.debug('Welcome message: %s', welcome_msg)
    credentials = await load_credentials()
    if not credentials:
        await register(reader, writer, nickname)
    else:
        await login(reader, writer)
    await send(writer, msg)
    writer.close()


if __name__ == '__main__':
    args = parse_args()
    log_level = 40 - (10 * args.verbose) if args.verbose > 0 else 0
    logger.setLevel(log_level)
    logger.info('Start main loop')
    asyncio.run(write_to_chat(args.host, args.port, args.msg, args.nickname))
