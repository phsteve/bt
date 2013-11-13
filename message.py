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
        else:
            self.type = message_types[ord(self.bytes[4])]
        self.message_len = struct.unpack('!i', bytes[:4])[0]
        self.payload = self.bytes[5:self.message_len+4]
        self.remainder = self.bytes[self.message_len+4:]

    @staticmethod
    def split_message(bytes, peer_id):
        messages = []
        message = Message(bytes, peer_id)
        bytes = message.remainder
        message.remainder = ''
        messages.append(message)
        while bytes:
            message = Message(bytes, peer_id)
            bytes = message.remainder
            message.remainder = ''
            messages.append(message)
        return messages




class MessageHandler(object):
    def __init__(self):
        self.handler = {'choke': self.choke_handler, 'unchoke': self.unchoke_handler, 'interested': self.interested_handler,
                        'not interested': self.notInterested_handler, 'have': self.have_handler, 'bitfield': self.bitfield_handler,
                        'request': self.request_handler, 'piece': self.piece_handler, 'cancel': self.cancel_handler, 'port': self.port_handler}

    def handle(self, message, controller):
        # import pdb
        # pdb.set_trace()
        self.handler[message.type](message, controller)

    def choke_handler(self, message, controller):
        controller.set_peer_status(message.peer_id, {'peer_choking':1})

    def unchoke_handler(self, message, controller):
        controller.set_peer_status(message.peer_id, {'peer_choking':0})

    def interested_handler(self, message, controller):
        controller.set_peer_status(message.peer_id, {'peer_interested':1})

    def notInterested_handler(self, message, controller):
        controller.set_peer_status(message.peer_id, {'peer_interested':0})

    def have_handler(self, message, controller):
        index = struct.unpack('!i', message.payload)[0]
        print 'index = ' + str(index)
        controller.set_peer_has_pieces_by_index(message.peer_id, index)


    def bitfield_handler(self, message, controller):
        # import pdb
        # pdb.set_trace()
        controller.set_peer_has_pieces(message.peer_id, bitstring.BitArray(bytes=message.payload))

            #set peer.has_pieces = bitfield

    def request_handler(self, message, controller):
        pass

    def piece_handler(self, message, controller):
        pass

    def cancel_handler(self, message, controller):
        pass

    def port_handler(self, message, controller):
        pass

    #info_hash
    #peer list
    #---