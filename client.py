import argparse
import asyncio
import logging
import json
from asyncio import StreamReader, StreamWriter
from typing import Optional

import aiofiles

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
    async with aiofiles.open('.credentials', 'w') as file:
        await file.write(credentials.decode().strip())


async def login(reader: StreamReader, writer: StreamWriter) -> None:
    credentials = await load_credentials()
    await send(writer, credentials['account_hash'])
    response = await reader.readline()
    if json.loads(response.strip()) is None:
        raise ValueError('Incorrect account_hash.')


async def write_to_chat(
        host: str, port: int, msg: str, nickname: Optional[str],
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
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
    asyncio.run(write_to_chat(args.host, args.port, args.nickname))
