from bt import Message
import bitstring

# {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
#                          4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
class Message(object):
    #deal with keep-alive message type

    def __init__(self, message, peer_id=None): #peer?
        message_types = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                         4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
        self.message = message
        self.peer_id = peer_id
        # self.peer_id = peer.peer_id
        # self.info_hash = peer.info_hash
        if not message:
            self.message_type = 'keep-alive'
        else:
            self.message_type = message_types[ord(self.message[4])]
        self.message_len = struct.unpack('!i', message[:4])[0] #this might not be right
        self.payload = self.message[5:]

def choke_handler():
    pass

def unchoke_handler():
    pass

def interested_handler():
    pass

def notInterested_handler():
    pass

def have_handler():
    pass

def bitfield_handler():
    

def request_handler():
    pass

def piece_handler():
    pass

def cancel_handler():
    pass

def port_handler():
    pass