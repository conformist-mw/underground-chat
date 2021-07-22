import argparse
import asyncio
import aiofiles
from datetime import datetime


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
    reader, writer = await asyncio.open_connection( host, port)
    cycles = 10
    while cycles:
        line = await reader.readline()
        msg = line.decode()
        date = datetime.now().strftime('%d.%m.%y %H:%M')
        full_msg = f'[{date}] {msg}'
        async with aiofiles.open(history_filepath, 'a') as file:
            await file.write(full_msg)
        print(full_msg.strip())
        cycles -= 1

    print('Close the connection')
    writer.close()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(connect_to_chat(args.host, args.port, args.history))
