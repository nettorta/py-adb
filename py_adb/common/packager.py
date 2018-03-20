import logging
import struct

from py_adb.adb_exceptions import InvalidChecksumError


logger = logging.getLogger(__name__)


class MessagePackager(object):
    """ ADB message packager """
    # (format, id, arg0, arg1, data len, data checksum, magic)
    def __init__(self):
        self.tags = [
            b'CNXN', b'AUTH', b'OPEN', b'WRTE', b'OKAY', b'CLSE',
            b'SYNC',
        ]
        self.magic = 0xFFFFFFFF
        self.fmt = b'<6I'  # An ADB message is 6 words in little-endian.

    @staticmethod
    def get_id_for_tag(tag):
        return sum(char << (idx * 8) for idx, char in enumerate(bytearray(tag)))

    def get_tag_for_id(self, id_):
        for tag in self.tags:
            if sum(char << (idx * 8) for idx, char in enumerate(bytearray(tag))) == id_:
                return tag
        else:
            raise ValueError('Unknown tag')

    def pack_header(self, message):
        logger.debug('Packing header for message: %s', message)
        return struct.pack(
            self.fmt,
            self.get_id_for_tag(message['tag']),
            message['arg0'],
            message['arg1'],
            len(message.get('data', b'')),
            self.checksum(message.get('data', b'')),
            self.get_id_for_tag(message['tag']) ^ self.magic
        )

    def unpack_header(self, message):
        logger.debug('Unpacking header: %s', message)
        try:
            id_, arg0, arg1, len_, checksum, _ = struct.unpack(self.fmt, message)
            tag = self.get_tag_for_id(id_)
        except struct.error:
            #logger.warning('Failed unpacking header %s', message, exc_info=True)
            raise
        else:
            unpacked_message = {
                'tag': tag,
                'arg0': arg0,
                'arg1': arg1,
                'data_len': len_,
                'checksum': checksum
            }
            logger.debug('Unpacked header: %s', unpacked_message)
            return unpacked_message

    def checksum(self, data):
        # The checksum is just a sum of all the bytes. I swear.
        if isinstance(data, bytearray):
            total = sum(data)
        elif isinstance(data, bytes):
            if data and isinstance(data[0], bytes):
                # Python 2 bytes (str) index as single-character strings.
                total = sum(map(ord, data))
            else:
                # Python 3 bytes index as numbers (and PY2 empty strings sum() to 0)
                total = sum(data)
        else:
            # Unicode strings (should never see?)
            total = sum(map(ord, data))
        return total & self.magic

    def verify(self, data, data_checksum):
        if self.checksum(data) != data_checksum:
            raise InvalidChecksumError('Data checksum verify failed %s != %s', (self.checksum(data), data_checksum))
