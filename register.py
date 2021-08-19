import asyncio
import logging
from contextlib import suppress
from functools import partial
from tkinter import CENTER, DISABLED, Button, Entry, Label, StringVar, Tk

import anyio

from auth import load_credentials, register, save_credentials
from gui import TkAppClosed, update_tk

# noinspection PyArgumentList
logging.basicConfig(
    format='{asctime} - {name} - {levelname} - {message} {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


def put_to_queue(name, queue):
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(partial(queue.put_nowait, name))


async def register_nickname(queue, user_input, hash_input):
    while True:
        name = await queue.get()
        logger.debug('Name: %s', name)
        credentials = await register('minechat.dvmn.org', 5050, name)
        logger.debug('Credentials: %s', credentials)
        await save_credentials(credentials)
        user_input.set(credentials['nickname'])
        hash_input.set(credentials['account_hash'])


async def draw(credentials, queue):
    root_frame = Tk()
    root_frame.geometry('400x150')
    root_frame.title('Registration')

    Label(root_frame, text='Nickname').grid(row=0, column=0)
    nickname_input = StringVar()
    Entry(root_frame, textvariable=nickname_input).grid(row=0, column=1)

    Label(root_frame, text='Account Hash').grid(row=1, column=0)
    hash_input = StringVar()
    Entry(root_frame, textvariable=hash_input, state=DISABLED).grid(
        row=1, column=1,
    )

    if nickname := credentials.get('nickname'):
        nickname_input.set(nickname)
    if account_hash := credentials.get('account_hash'):
        hash_input.set(account_hash)

    Button(
        root_frame,
        text='Register New Name',
        command=lambda: put_to_queue(nickname_input.get(), queue),
    ).place(relx=0.5, rely=0.6, anchor=CENTER)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(update_tk, root_frame)
        task_group.start_soon(
            register_nickname, queue, nickname_input, hash_input,
        )


async def main():
    credentials = await load_credentials()
    registration_queue = asyncio.Queue()

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(draw, credentials, registration_queue)


if __name__ == '__main__':
    with suppress(TkAppClosed, KeyboardInterrupt):
        asyncio.run(main())
