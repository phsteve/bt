from bencode import bencode, bdecode
import requests
import struct
import bitstring
from hashlib import sha1
from twisted.internet.protocol import Protocol, ClientFactory
import sys

from message import Message, generate_message

#general O-O organization feedback

#error handling (peer_id/info_hash mismatches, invalid bitfields etc)

MY_PEER_ID = '-SK0001-asdfasdfasdf'

class Controller(object):
    def __init__(self, torrent, received_file):
        self.peer_dict = {}
        self.torrent = torrent
        self.info_hash = torrent.info_hash
        self.message_handler = {'keep-alive': self.keepalive_handler, 'choke': self.choke_handler, 'unchoke': self.unchoke_handler, 'interested': self.interested_handler,
                                'not interested': self.notInterested_handler, 'have': self.have_handler, 'bitfield': self.bitfield_handler,
                                'request': self.request_handler, 'piece': self.piece_handler, 'cancel': self.cancel_handler, 'port': self.port_handler}
        self.received_file = received_file
        # self.data_list = ['' for _ in xrange(self.torrent.num_pieces)]
        self.piece_status = bitstring.BitArray('0b' + self.torrent.num_pieces * '0')
        self.pieces_requested = bitstring.BitArray('0b' + self.torrent.num_pieces * '0')#{piece_index: [done?, [(begin, end) for each chunk received]]}


    def handle(self, message):
        self.message_handler[message.type](message)

    def add_peer(self, peer):
        self.peer_dict[peer.peer_id] = peer
        # self.connect(peer)

    def set_peer_status(self, peer_id, status_values):
        for key in status_values:
            self.peer_dict[peer_id].status[key] = status_values[key]

    def set_peer_has_pieces(self, peer_id, bitstr):
        self.peer_dict[peer_id].has_pieces = bitstr

    def set_peer_has_pieces_by_index(self, peer_id, index):
        self.peer_dict[peer_id].has_pieces.overwrite('0b1', index)

    ##message handlers###################################

    def keepalive_handler(self, message):
        pass

    def choke_handler(self, message):
        self.set_peer_status(message.peer_id, {'peer_choking':1})

    def unchoke_handler(self, message):
        self.set_peer_status(message.peer_id, {'peer_choking':0})

    def interested_handler(self, message):
        self.set_peer_status(message.peer_id, {'peer_interested':1})
        self.send_control_message('unchoke')

    def notInterested_handler(self, message):
        self.set_peer_status(message.peer_id, {'peer_interested':0})

    def have_handler(self, message):
        index = struct.unpack('!i', message.payload)[0]
        self.set_peer_has_pieces_by_index(message.peer_id, index)


    def bitfield_handler(self, message):
        self.set_peer_has_pieces(message.peer_id, bitstring.BitArray(bytes=message.payload))

    def request_handler(self, req):
        # <len=0013><id=6><index><begin><length>
        self.received_file.seek(self.torrent.piece_length * req.index + req.begin)
        piece = generate_message('piece', index=req.index, begin=req.begin, block=self.received_file.read(req.length))
        self.peer_dict[req.peer_id].factory.transport.write(piece.bytes)
        

    def piece_handler(self, piece):
        # <len=0009+X><id=7><index><begin><block>
        # print "received piece # %s from %s" %(piece.index, self.peer_dict[piece.peer_id].ip)
        self.received_file.seek(piece.block_len * piece.index + piece.begin)
        self.received_file.write(piece.block)
        # self.data_list[piece.index] = piece.block
        self.piece_status.overwrite('0b1', piece.index)
        # print self.piece_status.bin
        if '0' not in self.piece_status.bin[:self.torrent.num_pieces-1]:
            from twisted.internet import reactor
            reactor.stop()


    def cancel_handler(self, message):
        pass

    def port_handler(self, message):
        pass

    ##message senders#########
    def get_next_piece(self):
        if '0' in self.pieces_requested.bin[:self.torrent.num_pieces]:
            return self.pieces_requested.bin.find('0')

    def send_control_message(self, type, peer_id):
        # sends a message (either choke, unchoke, interested, or not interested) to a peer
        msg = generate_message(type, peer_id=peer_id)
        self.peer_dict[peer_id].factory.transport.write(msg.bytes)

class TorrentFile(object):
    def __init__(self, filepath):
        self.f = open(filepath, 'rb').read()
        self.decoded = bdecode(self.f)
        self.announce_url = self.decoded['announce']
        self.info_hash = sha1(bencode(self.decoded['info'])).digest()
        self.info = self.decoded['info']
        self.piece_length = self.info['piece length']
        self.name = self.info['name']
        self.pieces = self.info['pieces']
        self.num_pieces = len(self.pieces)/20

class TrackerResponse(object):
    def __init__(self, torrent):
        self.request_payload = {'info_hash': torrent.info_hash,
                                'peer_id': MY_PEER_ID}
        self.peers_str = self.req_peers_from_tracker(torrent)
        self.peers = [Peer(peer_str, self.request_payload['info_hash']) for peer_str in self.peers_str]
        # make a dictionary of peer_id:peer pairs
    
    def req_peers_from_tracker(self, torrent):
        r = requests.get(torrent.announce_url, params=self.request_payload)
        response = bdecode(r.text)
        peers_str = response['peers']
        peers = []
        for i in range(len(peers_str)/6):
            peers.append(peers_str[6*i:6*(i+1)])
        return peers

class Peer(object):
    def __init__(self, peer_str, info_hash, factory=None, peer_id=None, shook_hands_already=False, handshake=None,
                 status={'am_choking': 1,'am_interested': 0, 'peer_choking': 1, 'peer_interested':0}):
        self.ip, self.port = self.parse_peer_str(peer_str)
        self.factory = factory

        #probably kill this
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.handshake = handshake
        self.has_pieces = 0
        self.status = status # status is 4-item dict, values of am_choking, am_interested, peer_choking, peer_interested
        self.messages_received = []
        # self.payload = payload

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = 256*ord(peer_str[-2]) + ord(peer_str[-1])
        return ip, port

    def connect(self, controller):
        from twisted.internet import reactor
        self.factory = PeerClientFactory(self, controller)
        reactor.connectTCP(self.ip, self.port, self.factory)
        # print 'attempting to connect to ' + self.ip + ':' + str(self.port)

class Handshake(object):
    # should this inherit from Message?
    def __init__(self, info_hash, pstr='BitTorrent protocol', reserved='\x00\x00\x00\x00\x00\x00\x00\x00', peer_id=MY_PEER_ID):
        self.pstr = pstr
        self.pstrlen = chr(len(self.pstr))
        self.reserved = reserved
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id

class PeerProtocol(Protocol):

    def __init__(self, factory, controller):
        self.factory = factory
        self.controller = controller
        self.shook_hands = False
        self._buffer = ''
        # self.deferred = deferred



    def connectionMade(self):
        # print 'connection made to ' + self.factory.peer.ip
        # import pdb
        # pdb.set_trace()
        sent_handshake = Handshake(self.controller.info_hash).handshake
        self.transport.write(sent_handshake)

    def is_handshake(self, bytes):
        if bytes[1:20] == 'BitTorrent protocol':
            return True

    def handle_handshake(self, bytes, messages, buff):
        pstr = bytes[1:20]
        reserved = bytes[20:28]
        info_hash = bytes[28:48]
        peer_id = bytes[48:68]
        # implement peer_id/info_hash checking
        # else:
            #need to check if peer already shook hands
        received_handshake = Handshake(info_hash, pstr=pstr, reserved=reserved,
                                       peer_id=peer_id)
        self.factory.peer.peer_id = peer_id
        self.controller.add_peer(self.factory.peer)
        self.shook_hands = True
        self.controller.peer_dict[peer_id].handshake = received_handshake
        # print 'handshake received: ' + received_handshake.handshake
    
        inter = generate_message('interested')
        # print 'sent an interested to %r' %(self.transport.getPeer())
        self.transport.write(inter.bytes)
        self.controller.peer_dict[peer_id].status['am_interested'] = 1
        buff = buff[68:]
        messages, buff = Message.split_message(buff, peer_id)
        return messages, buff
        

    def dataReceived(self, bytes):
        messages = []
        self._buffer += bytes
        # print 'bytes received: ' + repr(bytes)
        if not self.shook_hands:
            if len(self._buffer) >= 68:
                if self.is_handshake(bytes):
                    messages, self._buffer = self.handle_handshake(bytes, messages, self._buffer)


            #check if peer_id and info_hash are correct
            #if they're not, disconnect

        else:
            peer_id = self.factory.peer.peer_id
            messages, self._buffer = Message.split_message(self._buffer, peer_id)
            for message in messages:
                # print 'len of messages is: %d' %len(messages)
                # print 'received a %s from %s' %(message.type, peer_id)
                self.controller.peer_dict[peer_id].messages_received.append(message) #time stamp messages?
                self.controller.handle(message)

            next = self.controller.get_next_piece()

            if next is not None:
                req = generate_message('request', index=next, begin=0, length=2**14)
                self.transport.write(req.bytes)
                # print 'sent req for index %r to %r' %(str(req.index), self.transport.getPeer())
                self.controller.pieces_requested.overwrite('0b1', next)


    def connectionLost(self, reason):
        # print 'connection lost from: ' + self.factory.peer.ip

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, peer, controller):
        self.peer = peer
        self.controller = controller

    def buildProtocol(self, addr):
        return PeerProtocol(self, self.controller)

def main():
    torrent = TorrentFile('torrents/flagfromserver.torrent')
    received_file = open(torrent.name, 'wb')
    controller = Controller(torrent, received_file)
    tracker_response = TrackerResponse(torrent)
    peers = tracker_response.peers
    #this needs to be changed to update when the controller gets new peers from the tracker
    for peer in peers:
        peer.connect(controller)
        

    from twisted.internet import reactor
    reactor.run()


if __name__ == '__main__':
    main()


