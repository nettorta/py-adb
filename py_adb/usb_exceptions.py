"""Common exceptions for ADB """


class CommonUsbError(Exception):
    """Base class for handlers communication errors."""


class FormatMessageWithArgumentsException(CommonUsbError):
    """Exception that both looks good and is functional.

    Okay, not that kind of functional, it's still a class.

    This interpolates the message with the given arguments to make it
    human-readable, but keeps the arguments in case other code try-excepts it.
    """

    def __init__(self, message, *args):
        message %= args
        super(FormatMessageWithArgumentsException, self).__init__(message, *args)


class DeviceNotFoundError(FormatMessageWithArgumentsException):
    """Device isn't on USB."""


class DeviceAuthError(FormatMessageWithArgumentsException):
    """Device authentication failed."""


class LibusbWrappingError(CommonUsbError):
    """Wraps libusb1 errors while keeping its original usefulness.

    Attributes:
      usb_error: Instance of libusb1.USBError
    """

    def __init__(self, msg, usb_error):
        super(LibusbWrappingError, self).__init__(msg)
        self.usb_error = usb_error

    def __str__(self):
        return '%s: %s' % (
            super(LibusbWrappingError, self).__str__(), str(self.usb_error))


class WriteFailedError(LibusbWrappingError):
    """Raised when the device doesn't accept our command."""


class ReadFailedError(LibusbWrappingError):
    """Raised when the device doesn't respond to our commands."""


class AdbCommandFailureException(Exception):
    """ADB Command returned a FAIL."""


class AdbOperationException(Exception):
    """Failed to communicate over adb with device after multiple retries."""


class TcpTimeoutException(FormatMessageWithArgumentsException):
    """TCP connection timed out in the time out given."""
