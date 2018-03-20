class AuthSigner(object):
    """Signer for use with authenticated ADB, introduced in 4.4.x/KitKat."""

    def sign(self, data):
        """Signs given data using a private key."""
        raise NotImplementedError()

    def get_public_key(self):
        """Returns the public key in PEM format without headers or newlines."""
        raise NotImplementedError()


class AdbClient(object):
    def connect(self):
        raise NotImplementedError()

    def auth(self, message):
        raise NotImplementedError()

    def open(self, local_id, destination):
        pass

    def send(self, message):
        raise NotImplementedError()

    def send_okay(self, message):
        raise NotImplementedError()

    def read(self):
        raise NotImplementedError()


class Handler(object):
    def __init__(self):
        self.handle = None

    def open(self):
        raise NotImplementedError()

    def read(self, length):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()
