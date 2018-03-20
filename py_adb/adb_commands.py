""" A libusb1-based ADB reimplementation
Inspired by https://github.com/google/python-adb
"""

import socket
import logging
import queue as q
import usb1

from py_adb.adb_exceptions import InvalidResponseError
from py_adb.usb_exceptions import DeviceAuthError, ReadFailedError
from py_adb.common.interfaces import AdbClient
from py_adb.common.packager import MessagePackager
from py_adb.handle import HandlerFactory

from netort.data_processing import Drain, get_nowait_from_queue

logger = logging.getLogger(__name__)


class IncomingRouter(object):
    def __init__(self, client, sessions, pending_data):
        self.client = client
        self.sessions = sessions
        self.pending_data = pending_data

    def __iter__(self):
        while True:
            try:
                message = self.client.read()
                if message:
                    remote_id = message['arg0']
                    local_id = message['arg1']
                    if message['tag'] == b'OKAY':
                        self.sessions[local_id].register(remote_id)
                    elif message['tag'] == b'WRTE':
                        self.sessions[local_id].put(message['data'])
            except usb1.USBErrorIO:
                logger.warning('Something nasty happened. '
                               'Probably you are trying to send more data than USB buffer can handle.')
                self.client.close_handler()
                raise
            except usb1.USBError:
                logger.error('USB device error', exc_info=True)
                raise
            except Exception:
                logger.warning('Something nasty happened in message router', exc_info=True)
                raise


class AdbSessionManager(object):
    """ Device session manager """
    def __init__(self, source, rsa_keys=None, timeout=10000):
        self.source = source
        self.rsa_keys = rsa_keys
        self.timeout = timeout
        self.connected = False
        self.client = None
        self.sessions = {}
        self.pending_data = {}
        self.in_messages = q.Queue()
        self.in_messages_drain = None
        self.router = None

    def open_session(self, command):
        if not self.connected:
            try:
                logger.debug('Establishing connection')
                self.client = AdbUsbClient(self.source, self.rsa_keys)
                connected = self.client.connect()
                logger.info('Connected: %s', connected)
                self.connected = True
            except usb1.USBError:
                logger.error('USB error trying to establish connection to the phone', exc_info=True)
                self.client.close_handler()
                raise
        if not self.router:
            self.start_processing()

        local_id = len(self.sessions)+1
        self.sessions[local_id] = AdbSession(local_id, self.client, command)

        return self.sessions[local_id]

    def start_processing(self):
        self.router = IncomingRouter(self.client, self.sessions, self.pending_data)
        self.in_messages_drain = Drain(self.router, self.in_messages)
        self.in_messages_drain.start()

    def close_session(self, local_id):
        if not self.check_if_session_and_connection_exists(local_id):
            return
        else:
            self.sessions[local_id].close()

    def check_if_session_and_connection_exists(self, local_id):
        if not self.connected or not self.sessions:
            logger.warning(
                'Device not connected or no active sessions found! I\'m not a teapot! Open session first', exc_info=True
            )
            return
        if not self.sessions[local_id]:
            logger.warning('Session %s not found', local_id)
            return
        return True


class AdbSession(object):
    def __init__(self, local_id, client, command):
        self.incoming_session_data = q.Queue()
        self.local_id = local_id
        self.remote_id = None
        self.client = client
        self.client.open(local_id, command)
        self.finished = False

    def send_okay(self):
        logger.debug('Sending OKAY for successfull write')
        msg = dict(
            tag=b'OKAY',
            arg0=self.local_id,
            arg1=self.remote_id
        )
        self.client.send(msg)

    def register(self, remote_id):
        if not self.remote_id:
            self.remote_id = remote_id
        else:
            logger.warning('remote id %s already registered!', remote_id)
            raise RuntimeError('Something nasty happened')

    def get(self):
        while True:
            yield get_nowait_from_queue(self.incoming_session_data)
            if self.finished:
                break

    def put(self, data):
        self.incoming_session_data.put(data)
        self.send_okay()

    def close(self):
        msg = dict(
            tag=b'CLSE',
            arg0=self.local_id,
            arg1=self.remote_id
        )
        self.client.send(msg)

    def is_finished(self):
        return self.finished


class AdbUsbClient(AdbClient):
    """ Device client """

    VERSION = 0x01000000  # ADB protocol version.

    def __init__(self, source, rsa_keys, timeout=10000):
        self.timeout = timeout
        self.usb_handler = HandlerFactory().get_handler(source)
        self.rsa_keys = rsa_keys
        self.packager = MessagePackager()
        self.max_packet_size = 4096
        self.banner = socket.getfqdn().encode()
        self.auth_token, self.auth_signature, self.auth_rsapubkey = 1, 2, 3

    def send(self, message):
        logger.debug('Sending message: %s', message['tag'])
        self.usb_handler.write(self.packager.pack_header(message))
        self.usb_handler.write(message.get('data', b''))

    def send_okay(self, message):
        message = dict(
            tag=b'OKAY',
            arg0=message['arg1'],
            arg1=message['arg0']
        )
        self.send(message)

    def connect(self):
        logger.info('Starting connect()')
        message = dict(
            tag=b'CNXN',
            arg0=self.VERSION,
            arg1=self.max_packet_size,
            data=b'host::%s\0' % self.banner
        )
        self.send(message)
        connect_message = self.read_until_tag([b'CNXN', b'AUTH'])
        if connect_message['tag'] == b'CNXN':
            return connect_message['data']
        elif connect_message['tag'] == b'AUTH':
            return self.auth(connect_message)
        else:
            raise RuntimeError("Connect to device failed")

    def auth(self, message):
        logger.debug('Starting auth()')
        if not self.rsa_keys:
            raise DeviceAuthError('Device authentication required')
        else:
            for rsa_key in self.rsa_keys:
                if message['arg0'] != self.auth_token:
                    raise InvalidResponseError('Unknown AUTH request: %s' % message)
                msg = dict(
                    tag=b'AUTH',
                    arg0=self.auth_signature,
                    arg1=0,
                    data=rsa_key.sign(message['data'])
                )
                self.send(msg)
                auth_message = self.read_until_tag([b'CNXN', b'AUTH'])
                if auth_message['tag'] == b'CNXN':
                    return auth_message['data']

            # None of the keys worked, so send a public key.
            msg = {
                'cmd': b'AUTH',
                'arg0': self.auth_rsapubkey,
                'arg1': 0,
                'data': self.rsa_keys[0].get_public_key() + b'\0'
            }
            self.send(msg)
            try:
                auth_message = self.read_until_tag([b'CNXN'])
            except ReadFailedError as e:
                if e.usb_error.value == -7:  # Timeout.
                    raise DeviceAuthError('Accept auth key on device, then retry.')
                raise
            else:
                return auth_message['data']

    def read(self):
        message = self.packager.unpack_header(
            self.usb_handler.read(24)
        )
        if not message['data_len']:
            data = b''
        else:
            logger.debug('Starting data read, len: %s', message['data_len'])
            data = bytearray()
            while message['data_len']:
                buffer_ = self.usb_handler.read(message['data_len'])
                if len(buffer_) != message['data_len']:
                    logger.warning("Data_length {} does not match actual number of bytes read: {}".format(
                        message['data_len'], len(buffer_))
                    )
                data += buffer_
                message['data_len'] -= len(buffer_)
            self.packager.verify(data, message['checksum'])
            logger.debug('Received packet body: %s', data)
        if message['tag'] == b'WRTE':
            self.send_okay(message)
        return {
            'tag': message['tag'],
            'arg0': message['arg0'],
            'arg1': message['arg1'],
            'data': bytes(data)
        }

    def read_until_tag(self, expecting_tags):
        logger.info('Waiting for response of %s', expecting_tags)
        while True:
            message = self.read()
            if message['tag'] in expecting_tags:
                return message

    def open(self, local_id, destination):
        message = {
            'tag': b'OPEN',
            'arg0': local_id,
            'arg1': 0,
            'data': destination+b'\0'
        }
        self.send(message)

    def close_handler(self):
        self.usb_handler.close()
