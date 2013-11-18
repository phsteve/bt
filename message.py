import bitstring
import struct

# {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
#                          4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
class Message(object):

    def __init__(self, bytes, peer_id=None): #peer?
        assert len(bytes) > 3, repr(bytes)
        message_types = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                         4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
        self.bytes = bytes
        self.peer_id = peer_id
        # self.peer_id = peer.peer_id
        # self.info_hash = peer.info_hash
        if not bytes:
            self.type = 'keep-alive'
            self.message_len = 0
            self.payload = ''
        else:
            self.type = message_types[ord(self.bytes[4])]
            self.message_len = struct.unpack('!i', bytes[:4])[0]
            self.payload = self.bytes[5:self.message_len+4]
            self.remainder = self.bytes[self.message_len+4:]
 
    @staticmethod
    def split_message(_buffer, peer_id):
        messages = []
        while _buffer:
            if len(_buffer) < 4:
                return messages, _buffer
            message_len = struct.unpack('!i', _buffer[:4])[0]
            if len(_buffer[4:]) < message_len:
                return messages, _buffer
            message = Message(bytes=_buffer[0:4+message_len], peer_id=peer_id)
            messages.append(message)
            _buffer = _buffer[4+message_len:]
        return messages, _buffer

def generate_message(message_len, type, piece_index=None, bitfield=None, index=None, begin=None, length=None, block=None):
    if type in [0, 1, 2, 3]:
        message_len = struct.pack('>i', 1)
        bytes = message_len + struct.pack('B', type)
    if type == 6:
        message_len = struct.pack('>i', 13)
        index = struct.pack('>i', index)
        begin = struct.pack('>i', begin)
        length = struct.pack('>i', length)
        bytes = message_len + struct.pack('B', type) + index + begin + length

    return Message(bytes)