from bencode import bencode, bdecode
import requests
from hashlib import sha1

class TorrentFile(object):
    def __init__(self, filepath):
        self.f = open(filepath, 'rb').read()
        self.decoded = bdecode(self.f)
        self.announce_url = self.decoded['announce']
        #import ipdb
        #ipdb.set_trace()
        self.request_payload = {'info_hash': sha1(bencode(self.decoded['info'])).digest(),
                                'peer_id': '-SK0001-asdfasdfasdf',
                                'left': self.decoded['info']['length']}
        self.peer_list = self.req_peers_from_tracker()
        self.peers = [Peer(peer_str) for peer_str in self.peer_list]

    def req_peers_from_tracker(self):
        #use requests to get peer list from the announce url
        r = requests.get(self.announce_url, params=self.request_payload)
        response = bdecode(r.text)
        peers_str = response['peers']
        peers = []
        for i in range(len(peers_str)/6):
            peers.append(peers_str[6*i:6*(i+1)])
        return peers

class Peer(object):
    def __init__(self, peer_str):
        self.ip, self.port = self.parse_peer_str(peer_str)
        #self.peer_id = peer_id (from tracker response)

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = str(256*ord(peer_str[-2]) + ord(peer_str[-1]))
        return ip, port

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, deferred):
        self.deferred = deferred



class PeerHandshakeProtocol(Protocol):
    def __init__(self): #
        self.handshake = Handshake()

def connect_to_peer(ip, port):
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PeerClientFactory(d)
    reactor.connectTCP(ip, port, factory)
    return d

class Handshake(object):
    def __init__(self):
        

def handshake(peer):
    #shakes hands with one peer
    #TODO multiple peer support
    ip, port = peer.ip, peer.port

    from twisted.internet import reactor
    handshakes = []
    errors = []

    def got_handshake(handshake):
        handshakes.append(handshake)

    def handshake_failed(err):
        errors.append(err)

    def handshake_done(_):
        if len(handshakes) + len(errors) == len()

torrent = TorrentFile('torrents/flagfromserver.torrent')

import pdb
pdb.set_trace()