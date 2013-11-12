from bencode import bencode, bdecode
import requests
import struct
from hashlib import sha1
from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory

from message import Message, MessageHandler

# import handlers

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
        self.has_pieces = 0 ####
        self.status = status # status is 4-item dict, values of am_choking, am_interested, peer_choking, peer_interested
        # self.payload = payload

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = 256*ord(peer_str[-2]) + ord(peer_str[-1])
        return ip, port

class Handshake(object):
    # should this inherit from Message?
    def __init__(self, info_hash, pstr='BitTorrent protocol', reserved='\x00\x00\x00\x00\x00\x00\x00\x00', peer_id=MY_PEER_ID):
        # self.peer = peer
        self.pstr = pstr
        self.pstrlen = chr(len(self.pstr))
        self.reserved = reserved
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id

class PeerProtocol(Protocol):
    buff = ''

    def __init__(self, factory, controller, deferred):
        self.factory = factory
        self.controller = controller
        self.deferred = deferred

    def connectionMade(self):
        # self.factory.peers.append(self)
        # handshake = Handshake().handshake
        # print 'sending ' + handshake
        # self.transport.write(handshake)
        # print 'sent the handshake'
        # pass
        print 'connection made to ' + self.factory.peer.ip
        # import pdb
        # pdb.set_trace()
        sent_handshake = Handshake(self.controller.info_hash).handshake
        self.transport.write(sent_handshake)
        #send handshake


    def dataReceived(self, data):
        #buffer handling
        print 'data received: ' + data

        if data[1:20] == 'BitTorrent protocol':
            pstr = data[1:20]
            reserved = data[20:28]
            info_hash = data[28:48]
            peer_id = data[48:]
            # implement peer_id/info_hash checking
            # if peer_id not in self.factory.peer_dict:
            #     self.transport.loseConnection()
                #deal with info_hash
            # else:
                #need to check if peer already shook hands
                # self.factory.peer_dict[peer_id] = Peer()
            received_handshake = Handshake(info_hash, pstr=pstr, reserved=reserved,
                                           peer_id=peer_id)
            self.factory.peer.peer_id = peer_id
            self.controller.add_peer(self.factory.peer)
            self.controller.peer_dict[peer_id].shook_hands_already = True
            print 'handshake received: ' + received_handshake.handshake

            #check if peer_id and info_hash are correct
            #if they're not, disconnect

            # received_handshake = Handshake()
        elif not data:
            pass
        else:
            peer_id = self.factory.peer.peer_id
            received_message = Message(data, peer_id=peer_id)
            self.controller.message_handler.handle(received_message, self.controller)
            # import pdb
            # pdb.set_trace()
            print 'message received: ' + received_message.message
            self.deferred.callback(received_message.message)

    def connectionLost(self, reason):
        print 'connection lost from: ' + self.factory.peer.ip

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, deferred, peer, controller):
        self.deferred = deferred
        self.peer = peer
        self.controller = controller

    def buildProtocol(self, addr):
        return PeerProtocol(self, self.controller, self.deferred)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)



def connect(peer, controller):
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PeerClientFactory(d, peer, controller)
    reactor.connectTCP(peer.ip, peer.port, factory)
    print 'attempting to connect to ' + peer.ip + ':' + str(peer.port)
    return d



def main():
    # errors = []
    torrent = TorrentFile('torrents/flagfromserver.torrent')
    controller = Controller(torrent)
    tracker_response = TrackerResponse(torrent)
    peers = tracker_response.peers
    #this needs to be changed to update when the controller gets new peers from the tracker
    for peer in peers:
        connect(peer, controller)
        # d.addCallbacks(data_finished, data_failed)
    # import pdb
    # pdb.set_trace()


    from twisted.internet import reactor
    reactor.run()
    import pdb
    pdb.set_trace()

    
    # errors = []

main()


