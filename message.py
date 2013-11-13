import bitstring
import struct

# {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
#                          4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
class Message(object):

    def __init__(self, message, peer_id=None): #peer?
        message_types = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                         4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
        self.message = message
        self.peer_id = peer_id
        # self.peer_id = peer.peer_id
        # self.info_hash = peer.info_hash
        if not message:
            self.type = 'keep-alive'
        else:
            self.type = message_types[ord(self.message[4])]
        self.message_len = struct.unpack('!i', message[:4])[0] #this might not be right
        self.payload = self.message[5:]

class MessageHandler(object):
    def __init__(self):
        self.handler = {'choke': self.choke_handler, 'unchoke': self.unchoke_handler, 'interested': self.interested_handler,
                        'not interested': self.notInterested_handler, 'have': self.have_handler, 'bitfield': self.bitfield_handler,
                        'request': self.request_handler, 'piece': self.piece_handler, 'cancel': self.cancel_handler, 'port': self.port_handler}

    def handle(self, message, controller):
        import pdb
        pdb.set_trace()
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
        pass


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