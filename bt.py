from bencode import bencode, bdecode
import requests
import struct
from hashlib import sha1
from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory

from message import Message, MessageHandler

#TODO: MessageHandler seems almost redundant, since I'm just doing everything in
#Controller anyway...

#general O-O organization feedback

#error handling (peer_id/info_hash mismatches, invalid bitfields etc)

#am I even using Twisted properly???

#doesn't connect to second peer.

#what should i do about testing?

#buffering

MY_PEER_ID = '-SK0001-asdfasdfasdf'

class Controller(object):
    def __init__(self, torrent):
        self.peer_dict = {}
        self.torrent = torrent
        self.info_hash = torrent.info_hash
        self.message_handler = MessageHandler()

    def add_peer(self, peer):
        self.peer_dict[peer.peer_id] = peer
        # self.connect(peer)

    def set_peer_status(self, peer, status_values):
        for key in status_values:
            self.peer_dict[peer.peer_id].status[key] = status_values[key]

    def set_peer_has_pieces(self, peer_id, bitstr):
        self.peer_dict[peer_id].has_pieces = bitstr

    def set_peer_has_pieces_by_index(self, peer_id, index):
        self.peer_dict[peer_id].has_pieces.overwrite('0b1', index)

class TorrentFile(object):
    def __init__(self, filepath):
        self.f = open(filepath, 'rb').read()
        self.decoded = bdecode(self.f)
        self.announce_url = self.decoded['announce']
        self.info_hash = sha1(bencode(self.decoded['info'])).digest()

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
    def __init__(self, peer_str, info_hash, peer_id=None, shook_hands_already=False,
                 status={'am-choking': 1,'am_interested': 0, 'peer_choking': 1, 'peer_interested':0}):
        self.ip, self.port = self.parse_peer_str(peer_str)
        #probably kill this
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.shook_hands_already = shook_hands_already
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
        factory = PeerClientFactory(self, controller)
        reactor.connectTCP(self.ip, self.port, factory)
        print 'attempting to connect to ' + self.ip + ':' + str(self.port)

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
    buff = ''

    def __init__(self, factory, controller):
        self.factory = factory
        self.controller = controller
        # self.deferred = deferred

    def connectionMade(self):
        print 'connection made to ' + self.factory.peer.ip
        # import pdb
        # pdb.set_trace()
        sent_handshake = Handshake(self.controller.info_hash).handshake
        self.transport.write(sent_handshake)

    def dataReceived(self, bytes):
        #buffer handling
        print 'bytes received: ' + repr(bytes)

        if bytes[1:20] == 'BitTorrent protocol':
            pstr = bytes[1:20]
            reserved = bytes[20:28]
            info_hash = bytes[28:48]
            peer_id = bytes[48:]
            # implement peer_id/info_hash checking
            # else:
                #need to check if peer already shook hands
            received_handshake = Handshake(info_hash, pstr=pstr, reserved=reserved,
                                           peer_id=peer_id)
            self.factory.peer.peer_id = peer_id
            self.controller.add_peer(self.factory.peer)
            self.controller.peer_dict[peer_id].shook_hands_already = True
            print 'handshake received: ' + received_handshake.handshake

            #check if peer_id and info_hash are correct
            #if they're not, disconnect

            #should i store the handshake somewhere?

        elif not bytes:
            pass
        else:
            peer_id = self.factory.peer.peer_id
            #message splitting
            messages = Message.split_message(bytes, peer_id)

            for message in messages:
                self.controller.peer_dict[message.peer_id].messages_received.append(message)
                self.controller.message_handler.handle(message, self.controller)
            import pdb
            pdb.set_trace()



            # self.controller.message_handler.handle(received_message, self.controller)
            # import pdb
            # pdb.set_trace()
            #print 'message received: ' + received_message.message

    def connectionLost(self, reason):
        print 'connection lost from: ' + self.factory.peer.ip

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, peer, controller):
        # self.deferred = deferred
        self.peer = peer
        self.controller = controller

    def buildProtocol(self, addr):
        return PeerProtocol(self, self.controller) #deferred

def main():
    torrent = TorrentFile('torrents/flagfromserver.torrent')
    controller = Controller(torrent)
    tracker_response = TrackerResponse(torrent)
    peers = tracker_response.peers
    #this needs to be changed to update when the controller gets new peers from the tracker
    for peer in peers:
        peer.connect(controller)
        #never gets to subsequent peers
    # import pdb
    # pdb.set_trace()


    from twisted.internet import reactor
    reactor.run()
    # import pdb
    # pdb.set_trace()

    
    # errors = []

main()


