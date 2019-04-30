from base58 import b58encode_check, b58decode_check
from pyblake2 import blake2b
import btcpy
from binascii import hexlify, unhexlify
from btcpy.structs.hd import ExtendedPrivateKey, ExtendedPublicKey
import secp256k1


TZ_VERSION = {
    'tz1': '0000',
    'tz2': '0001',
    'tz3': '0002'
}


def blake2b_32(v=b''):
    return blake2b(v, digest_size=32)


def numToZarith(num):
    bit_str = bin(num)[2:]
    while len(bit_str) % 7 is not 0:
        bit_str = '0' + bit_str
    result = ''
    for i in range(len(bit_str), 0, -7):
        bit_str_section = bit_str[i-7:i]
        if i is 7:
            bit_str_section = '0' + bit_str_section
        else:
            bit_str_section = '1' + bit_str_section
        hex_str = '{:x}'.format(int(bit_str_section, 2))
        if len(hex_str) % 2 == 1:
            hex_str = '0' + hex_str
        result += hex_str
    return result


class XPrv(object):
    def __init__(self, key):
        btcpy.setup.setup('mainnet')
        self.key = ExtendedPrivateKey.decode(key)

    def derive(self, path):
        return XPrv(self.key.derive(path).encode())

    def prv(self):
        spsk = b'\x11\xa2\xe0\xc9'
        return b58encode_check(spsk + self.key.key.serialize())

    def pub(self):
        sppk = b'\x03\xfe\xe2V'
        return b58encode_check(sppk + self.key.key.pub().serialize())

    def pkh(self):
        tz2 = b'\x06\xa1\xa1'
        pkh = blake2b(data=self.key.key.pub().serialize(), digest_size=20).digest()
        return b58encode_check(tz2 + pkh)


class XPub(object):
    def __init__(self, key):
        btcpy.setup.setup('mainnet')
        self.key = ExtendedPublicKey.decode(key)

    def derive(self, path):
        return XPub(self.key.derive(path).encode())

    def prv(self):
        sppk = b'\x03\xfe\xe2V'
        return b58encode_check(sppk + self.key.key.serialize())

    def pkh(self):
        tz2 = b'\x06\xa1\xa1'
        pkh = blake2b(data=self.key.key.serialize(), digest_size=20).digest()
        return b58encode_check(tz2 + pkh)


class Transaction(object):
    def __init__(self, branch, source, fee, counter, gas_limit, storage_limit, amount, destination):
        self.branch = branch
        self.source = source
        self.fee = fee
        self.counter = counter
        self.gas_limit = gas_limit
        self.storage_limit = storage_limit
        self.amount = amount
        self.destination = destination

    def _cleaned_address(self, addr):
        if addr[:2] == 'tz':
            return TZ_VERSION[addr[:3]] + hexlify(b58decode_check(addr)).decode()[6:]
        elif addr[:2] == 'KT':
            return '01' + hexlify(b58decode_check(addr)).decode()[6:] + '00'
        else:
            raise KeyError('Unknown address: {}'.format(addr))

    def serialize(self):
        result = hexlify(b58decode_check(self.branch)).decode()[4:]
        result += '08'  # tag for tx
        result += '0000'  # source version
        result += self._cleaned_address(self.source)
        result += numToZarith(self.fee)
        result += numToZarith(self.counter)
        result += numToZarith(self.gas_limit)
        result += numToZarith(self.storage_limit)
        result += numToZarith(self.amount)
        result += self._cleaned_address(self.destination)
        result += '00'  # params
        return result

    def signature(self, key):
        raw_tx = self.serialize()
        sk_str = b58decode_check(key)[4:]
        pk = secp256k1.PrivateKey(sk_str)
        signature = pk.ecdsa_serialize_compact(
            pk.ecdsa_sign(b'\x03' + unhexlify(raw_tx), digest=blake2b_32))
        return hexlify(signature)

    def signed(self, key):
        return self.serialize() + self.signature(key)
