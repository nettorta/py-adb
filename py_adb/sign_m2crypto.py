from M2Crypto import RSA

from py_adb.common.interfaces import AuthSigner


class M2CryptoSigner(AuthSigner):
    """AuthSigner using M2Crypto."""

    def __init__(self, rsa_key_path):
        with open(rsa_key_path + '.pub') as rsa_pub_file:
            self.public_key = rsa_pub_file.read()

        self.rsa_key = RSA.load_key(rsa_key_path)

    def sign(self, data):
        return self.rsa_key.sign(data, 'sha1')

    def get_public_key(self):
        return self.public_key
