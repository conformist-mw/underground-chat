import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__file__)


class ConnectionNotify:

    def __init__(self, queue, notify_class):
        self.queue = queue
        self.notify_class = notify_class

    def initiate(self):
        self.queue.put_nowait(self.notify_class.INITIATED)

    def establish(self):
        self.queue.put_nowait(self.notify_class.ESTABLISHED)

    def close(self):
        self.queue.put_nowait(self.notify_class.CLOSED)


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