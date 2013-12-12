import bitstring
import struct

# {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
#                          4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}



class Message(object):

    def __init__(self, bytes='', peer_id=''):
        assert len(bytes) > 3, repr(bytes)
        self.bytes = bytes
        self.peer_id = peer_id
        # self.peer_id = peer.peer_id
        # self.info_hash = peer.info_hash
        if bytes == '\x00\x00\x00\x00':
            self.type = 'keep-alive'
            self.message_len = 0
            self.payload = ''
        else:
            # import pdb
            # pdb.set_trace()
            self.type = digit_to_type[ord(self.bytes[4])]
            self.message_len = struct.unpack('!i', bytes[:4])[0]
            self.payload = self.bytes[5:self.message_len+4]
 
    @staticmethod
    def split_message(_buffer, peer_id):
        messages = []
        while _buffer:
            if len(_buffer) < 4:
                return messages, _buffer
            message_len = struct.unpack('>i', _buffer[:4])[0]
            if len(_buffer[4:]) < message_len:
                return messages, _buffer

            # message = Message(bytes=_buffer[0:4+message_len], peer_id=peer_id)
            message = interpret_bytes(_buffer[0:4+message_len], peer_id=peer_id)
            messages.append(message)
            _buffer = _buffer[4+message_len:]
        return messages, _buffer

class KeepAlive(Message):
    '''<len=0000>'''
    def __init__(self, bytes='', peer_id=''):
        if not bytes:
            bytes = struct.pack('>i', 0)
        super(KeepAlive, self).__init__(bytes=bytes)

class Choke(Message):
    '''<len=0001><id=0>'''
    def __init__(self, bytes='', peer_id=''):
        if not bytes:
            bytes = struct.pack('>i', 1) + struct.pack('b', 0)

        super(Choke, self).__init__(bytes=bytes, peer_id=peer_id)

class Unchoke(Message):
    '''<len=0001><id=1>'''
    def __init__(self, bytes='', peer_id=''):
        if not bytes:
            bytes = struct.pack('>i', 1) + struct.pack('b', 1)
        super(Unchoke, self).__init__(bytes=bytes, peer_id=peer_id)

class Interested(Message):
    '''<len=0001><id=2>'''
    def __init__(self, bytes='', peer_id=''):
        if not bytes:
            bytes = struct.pack('>i', 1) + struct.pack('b', 2)
        super(Interested, self).__init__(bytes=bytes, peer_id=peer_id)

class NotInterested(Message):
    '''<len=0001><id=3>'''
    def __init__(self, bytes='', peer_id=''):
        if not bytes:
            bytes = struct.pack('>i', 1) + struct.pack('b', 3)
        super(NotInterested, self).__init__(bytes=bytes)

class Have(Message):
    '''<len=0005><id=4><piece index>'''
    def __init__(self, bytes='', piece_index='', peer_id=''):
        if bytes:
            self.bytes = bytes
        if not bytes:
            self.peer_id = peer_id
            self.message_len = struct.pack('>i', 5)
            self.type = 'have'
            self.piece_index = piece_index
            self.bytes = self.message_len + struct.pack('b', 4) + struct.pack('>i', self.piece_index)
        super(Have, self).__init__(bytes=(self.bytes), peer_id=peer_id)

class Bitfield(Message):
    '''<len=0001+X><id=5><bitfield>'''
    def __init__(self, bytes='', bitfield_len=0, bitfield='', peer_id=''):
        if bytes:
            self.bitfield_len = struct.unpack('>i', bytes[:4])[0] - 1
            super(Bitfield, self).__init__(bytes=bytes, peer_id=peer_id)
            self.bitfield = bitstring.BitArray(bytes=self.payload)
        else:
            self.bitfield_len = bitfield_len
            self.message_len = struct.pack('>i', 1 + bitfield_len)
            # self.type = 'bitfield'
            self.bitfield = bitfield
            self.bytes = self.message_len + struct.pack('b', 5) + struct.pack('s', self.bitfield)
            super(Bitfield, self).__init__(bytes=bytes, peer_id=peer_id)

            #self.bytes may be wrong

class Request(Message):
    '''<len=0013><id=6><index><begin><length>'''

    def __init__(self, bytes='', peer_id='', index=0, begin=0, length=0):
        if bytes:
            self.index = struct.unpack('>i', bytes[5:9])[0]
            self.begin = struct.unpack('>i', bytes[9:13])[0]
            self.length = struct.unpack('>i', bytes[13:17])[0]
            self.peer_id = peer_id
        else:
            self.message_len = 13
            self.index = index
            self.begin = begin
            self.length = length
            self.bytes = ''.join([struct.pack('>i', self.message_len), struct.pack('b', 6), struct.pack('>i', self.index), struct.pack('>i', self.begin), struct.pack('>i', self.length)])
        super(Request, self).__init__(bytes=self.bytes, peer_id=peer_id)

class DiffRequest(Message):
    def __init__(self, index, begin, length):
        message_len = 13
        bytes = ''.join([struct.pack('>i', message_len), struct.pack('b', 6), struct.pack('>i', index), struct.pack('>i', begin), struct.pack('>i', length)])
        super(DiffRequest, self).__init__(bytes=bytes)

class Piece(Message):
    '''<len=0009+X><id=7><index><begin><block>'''
    def __init__(self, bytes='', peer_id='', index=0, begin=0, block=''):
        if bytes:
            self.bytes = bytes
            self.index = struct.unpack('>i', bytes[5:9])[0]
            self.begin = struct.unpack('>i', bytes[9:13])[0]
            self.block = bytes[13:]
            self.block_len = len(self.block)
            self.peer_id = peer_id
        else:
            self.block_len = len(block)
            self.index = index
            self.begin = begin
            self.block = block
            self.bytes = ''.join([struct.pack('>i', 9 + self.block_len), struct.pack('h', 7), struct.pack('>i', self.index), struct.pack('>i', self.begin), self.block])
        super(Piece, self).__init__(bytes=self.bytes, peer_id=peer_id)

class Cancel(Message):
    '''cancel: <len=0013><id=8><index><begin><length>'''
    pass

class Port(Message):
    '''<len=0003><id=9><listen-port>'''
    pass

digit_to_type = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                 4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port',
                 'choke': 0, 'unchoke': 1, 'interested': 2, 'not interested': 3,
                 'have': 4, 'bitfield': 5, 'request': 6, 'piece': 7, 'cancel': 8, 'port': 9}

type_to_class = {'choke': Choke, 'unchoke': Unchoke, 'interested': Interested, 'not interested': NotInterested,
         'have': Have, 'bitfield': Bitfield, 'request': Request, 'piece': Piece, 'cancel': Cancel, 'port': Port}


def generate_message(type, **kwargs):
    message = type_to_class[type](bytes='', **kwargs)
    return message

def interpret_bytes(bytes, peer_id):
    if len(bytes) > 4:
        type = ord(bytes[4])
    else:
        type = 0
    message = type_to_class[digit_to_type[type]](bytes=bytes, peer_id=peer_id) #yuck
    return message