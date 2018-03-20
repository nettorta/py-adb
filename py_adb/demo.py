from py_adb import sign_m2crypto
from py_adb.adb_commands import AdbSessionManager

import os
import logging
import time

logger = logging.getLogger(__name__)


def main():
    fmt = "%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d\t%(message)s"
    logging.basicConfig(level='INFO', format=fmt)
    signer = sign_m2crypto.M2CryptoSigner(os.path.expanduser('~/.android/adbkey'))
    manager = AdbSessionManager('3709e945', rsa_keys=[signer])
    session = {}
    for x in xrange(5):
        logger.info('Starting session %s', x)
        session[x] = manager.open_session(command=b'shell:echo "123"')

    logger.info('Sleep 3 seconds...')
    time.sleep(3)
    for x in xrange(5):
        for chunk in session[x].get():
            if chunk:
                print chunk
                break


if __name__ == "__main__":
    fmt = "%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d\t%(message)s"
    logging.basicConfig(level='INFO', format=fmt)
    main()
