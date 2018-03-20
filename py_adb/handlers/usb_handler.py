import usb1
import logging
import weakref

import libusb1
from py_adb.common.interfaces import Handler

logger = logging.getLogger(__name__)


class UsbHandler(Handler):
    """ Usb handler"""
    USB_SETTINGS = (0xFF, 0x42, 0x01)  # (class, subclass, proto), adb.h

    def __init__(self, source, timeout=10000):
        super(UsbHandler, self).__init__()
        self.context = usb1.USBContext()
        self.source = source
        self.source_type = 'usb' if self.source.startswith('usb:') else 'serial'
        self.interface_number = None
        self.__max_read_packet_len = 0
        self.device, self.settings = self.get_device()
        self.__get_endpoints()
        self.open()
        self.timeout = timeout

    def _get_related_usb_devices(self):
        return [
            (device, settings)
            for device in self.context.getDeviceList(skip_on_error=True) for settings in device.iterSettings()
            if (settings.getClass(), settings.getSubClass(), settings.getProtocol()) == self.USB_SETTINGS
        ]

    def get_device(self):
        devices_list = self._get_related_usb_devices()
        logger.debug('Related devices list: %s', devices_list)
        matched_devices = None
        if devices_list:
            if self.source_type == 'usb':
                matched_devices = [
                    (device, settings) for device, settings in devices_list
                    if [device.getBusNumber()] + device.getPortNumberList() == self.source
                ]
            elif self.source_type == 'serial':
                matched_devices = [
                    (device, settings) for device, settings in devices_list
                    if device.getSerialNumber() == self.source
                ]
            else:
                matched_devices = []
        else:
            raise ValueError('No devices found. Is it plugged in and in appropriate state?')
        logger.debug('Matched devices list: %s', matched_devices)
        if not matched_devices:
            raise ValueError('No suitable devices found for source: %s', self.source)
        if len(matched_devices) > 1:
            raise ValueError(
                'There are more than 1 devices found for this source: %s. Devices: %s',
                self.source, matched_devices
            )
        return matched_devices[0]

    def __get_endpoints(self):
        for endpoint in self.settings.iterEndpoints():
            address = endpoint.getAddress()
            if address & libusb1.USB_ENDPOINT_DIR_MASK:
                self.__read_endpoint = address
                self.__max_read_packet_len = endpoint.getMaxPacketSize()
            else:
                self.__write_endpoint = address
        if not self.__read_endpoint or not self.__write_endpoint:
            raise RuntimeError('USB endpoints not found')

    def open(self):
        handle = self.device.open()
        interface = self.settings.getNumber()
        if handle.kernelDriverActive(interface):
            handle.detachKernelDriver(interface)
        handle.claimInterface(interface)
        self.handle = handle
        self.interface_number = interface
        logger.debug('Opened usb handler: %s. Iface: %s', self.handle, self.interface_number)
        weakref.ref(self, self.close)  # When this object is deleted, make sure it's closed.

    def close(self):
        logger.info('Closing handle...')
        try:
            self.handle.releaseInterface(self.interface_number)
            self.handle.close()
            del self.handle
        except usb1.USBError:
            logger.warning('USBError while closing handle %s:', exc_info=True)
        finally:
            self.handle = None

    def flush(self):
        while True:
            self.read(self.__max_read_packet_len)

    def write(self, data):
        try:
            self.handle.bulkWrite(self.__write_endpoint, data, timeout=self.timeout)
        except usb1.USBError:
            logger.warning('Usb write failed, data: %s', data)
            raise

    def read(self, length):
        try:
            chunk = self.handle.bulkRead(self.__read_endpoint, length, timeout=self.timeout)
        except usb1.USBError:
            logger.warning('Usb read failed')
            raise
        else:
            return bytearray(chunk)
