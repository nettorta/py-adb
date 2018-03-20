class InvalidResponseError(Exception):
    """Got an invalid response to our command."""


class InvalidChecksumError(Exception):
    """Checksum of data didn't match expected checksum."""
