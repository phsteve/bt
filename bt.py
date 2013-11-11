from bencode import bencode, bdecode
import requests
import struct
from hashlib import sha1
from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory

MY_PEER_ID = '-SK0001-asdfasdfasdf'


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
    def __init__(self, peer_str, info_hash, peer_id=None, shook_hands_already=False):
        self.ip, self.port = self.parse_peer_str(peer_str)
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.shook_hands_already = shook_hands_already
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

class Message(object):
    #deal with keep-alive message type

    def __init__(self, message): #peer?
        message_types = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                         4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
        self.message = message
        # self.peer_id = peer.peer_id
        # self.info_hash = peer.info_hash
        if not message:
            self.message_type = 'keep-alive'
        else:
            self.message_type = message_types[ord(self.message[4])]
        self.message_len = struct.unpack('!i', message[:4])[0] #this might not be right
        self.payload = self.message[5:]

class PeerProtocol(Protocol):
    response = ''

    def __init__(self, factory, info_hash):
        self.factory = factory
        self.info_hash = info_hash

    def connectionMade(self):
        # self.factory.peers.append(self)
        # handshake = Handshake().handshake
        # print 'sending ' + handshake
        # self.transport.write(handshake)
        # print 'sent the handshake'
        # pass
        print 'connection made to ' + self.factory.peer.ip
        sent_handshake = Handshake(self.info_hash).handshake
        self.transport.write(sent_handshake)
        #send handshake


    def dataReceived(self, data):
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
            print 'handshake received: ' + received_handshake.handshake

            #check if peer_id and info_hash are correct
            #if they're not, disconnect

            # received_handshake = Handshake()
        else:
            import pdb
            pdb.set_trace()
            received_message = Message(data)
            print 'message received: ' + received_message.message

    def connectionLost(self, reason):
        print 'connection lost from: ' + self.factory.peer.ip

#peer dict should be in factory
class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, deferred, peer, info_hash):
        self.deferred = deferred
        self.peer = peer
        self.info_hash = info_hash

    def buildProtocol(self, addr):
        return PeerProtocol(self, self.info_hash)

    def data_finished(self, data):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(data)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_messages(peer, info_hash):
    # d = defer.DeferredList([defer.Deferred() for _ in peers])
    # from twisted.internet import reactor
    # #one factory per peer???
    # factory = PeerClientFactory(d)
    # reactor.connectTCP(peer.ip, peer.port, factory)
    # return d
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PeerClientFactory(d, peer, info_hash)
    reactor.connectTCP(peer.ip, peer.port, factory)
    print 'attempting to connect to ' + peer.ip + ':' + str(peer.port)
    return d


def main():
    errors = []
    torrent = TorrentFile('torrents/flagfromserver.torrent')
    tracker_response = TrackerResponse(torrent)
    peers = tracker_response.peers

    def got_data(data):
        print data

    def data_failed(err):
        errors.append(err)

    for peer in peers:
        d = get_messages(peer, torrent.info_hash)
        d.addCallbacks(got_data, data_failed)

    from twisted.internet import reactor
    reactor.run()


    
    errors = []

main()


