import asyncio
import logging
from contextlib import asynccontextmanager
from socket import gaierror

from anyio import sleep

SLEEP_TIMEOUT = 3

logger = logging.getLogger(__file__)
watchdog_logger = logging.getLogger('watchdog')


class ConnectionNotify:

    def __init__(self, queue, notify_class=None):
        self.queue = queue
        self.notify_class = notify_class

    def _get_attr(self, attr):
        return getattr(self.notify_class, attr, attr)

    def initiate(self):
        self.queue.put_nowait(self._get_attr('INITIATED'))

    def establish(self):
        self.queue.put_nowait(self._get_attr('ESTABLISHED'))

    def close(self):
        self.queue.put_nowait(self._get_attr('CLOSED'))


@asynccontextmanager
async def open_connection(host, port, notify: ConnectionNotify):
    logger.info('Initiate connection')
    notify.initiate()
    reader, writer = await asyncio.open_connection(host, port)
    logger.info('Connection established')
    notify.establish()
    try:
        yield reader, writer
    finally:
        logger.info('Close the connection')
        notify.close()
        writer.close()
        await writer.wait_closed()


def reconnect(func):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await func(*args, **kwargs)
            except (ConnectionError, gaierror):
                watchdog_logger.error('Got connection error')
                await sleep(SLEEP_TIMEOUT)
            except BaseException as e:
                watchdog_logger.error('Unhandled error: %r', e)
                await sleep(SLEEP_TIMEOUT)
    return wrapper
