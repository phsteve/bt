from bencode import bencode, bdecode
import requests
from hashlib import sha1
from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory

MY_PEER_ID = '-SK0001-asdfasdfasdf'

class TorrentFile(object):
    def __init__(self, filepath):
        self.f = open(filepath, 'rb').read()
        self.decoded = bdecode(self.f)
        self.announce_url = self.decoded['announce']
        #import ipdb
        #ipdb.set_trace()
        self.request_payload = {'info_hash': sha1(bencode(self.decoded['info'])).digest(),
                                'peer_id': MY_PEER_ID}
                                #'left': self.decoded['info']['length']}
        self.peer_list = self.req_peers_from_tracker()
        self.peers = [Peer(peer_str, self.request_payload['info_hash']) for peer_str in self.peer_list]
        #Is this a bad way of passing the info_hash to the Peer?

    def req_peers_from_tracker(self):
        r = requests.get(self.announce_url, params=self.request_payload)
        response = bdecode(r.text)
        peers_str = response['peers']
        peers = []
        for i in range(len(peers_str)/6):
            peers.append(peers_str[6*i:6*(i+1)])
        return peers

class Peer(object):
    def __init__(self, peer_str, info_hash, shook_hands_already=False, payload=None):
        self.ip, self.port = self.parse_peer_str(peer_str)
        self.info_hash = info_hash
        self.shook_hands_already = shook_hands_already
        self.payload = payload
        #self.peer_id = peer_id (from tracker response)

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = 256*ord(peer_str[-2]) + ord(peer_str[-1])
        return ip, port


class PeerProtocol(Protocol):
    response = ''

    def dataReceived(self, data):
        print data
        self.response += data

    def connectionMade(self):
        print 'connection made to ' + self.factory.peer.ip
        # if not self.factory.peer.shook_hands_already:
        handshake = Handshake(self.factory.peer).handshake
        self.factory.peer.shook_hands_already = True
        print 'sent ' + handshake
        self.transport.write(handshake)

    def connectionLost(self, reason):
        print 'connection lost from ' + self.factory.peer.ip

    # def dataReceived(self, response):
    #     self.factory.data_finished(response)

    # def send_data(self, data):
    #     self.transport.write(data)


    #INTERFACES

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, deferred, peer):
        self.deferred = deferred
        self.peer = peer

    def data_finished(self, data):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(data)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

class Handshake(object):
    # should this inherit from Message?
    def __init__(self, peer):
        self.peer = peer
        self.pstr = 'BitTorrent protocol'
        self.pstrlen = chr(len(self.pstr))
        self.reserved = '\x00\x00\x00\x00\x00\x00\x00\x00'
        self.info_hash = peer.info_hash
        self.peer_id = MY_PEER_ID
        self.handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id
        #self.expected_return_peer_id = peer.peer_id
        #TODO verify that the return handshake's info_hash and peer_id are accurate

class Message(object):
    def __init__(self, message, peer):
        self.message = message
        self.peer_id = None
        self.info_hash = None

    #if message is a handshake:
    #   parse message, check that peer_id and info_hash match

    #else:
    #   do something else


def get_data(peer):
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PeerClientFactory(d, peer)
    reactor.connectTCP(peer.ip, peer.port, factory)
    print 'attempting to connect to ' + peer.ip + ':' + str(peer.port)
    return d

def main(peers):
    
    from twisted.internet import reactor
    
    data = []
    errors = []

    def got_data(datum):
        data.append(datum)

    def data_failed(err):
        errors.append(err)

    def data_done(_):
        if len(data) + len(errors) == len(peers):
            reactor.stop()

    for peer in peers:
        #ip, port = peer.ip, peer.port
        # print peer.ip
        # print peer.port
        d = get_data(peer)
        if d:
            d.addCallbacks(got_data, data_failed)
            d.addBoth(data_done)

    reactor.run()

    # for datum in data:
    #     print datum

torrent = TorrentFile('torrents/flagfromserver.torrent')
main(torrent.peers)

# import pdb
# pdb.set_trace()