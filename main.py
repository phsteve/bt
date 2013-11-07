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
        print 'data received ' + data
        self.response += data
        #set peer.peer_id to peer_id from h
        # print Message(data, self.factory.peer)
        # self.factory.deferred.callback(data)
        #can I callback parse_handshake here?
        got_data(self.response)

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
        print 'in data_finished'
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(data)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

class Handshake(object):
    # should this inherit from Message?
    def __init__(self, peer, pstr='BitTorrent protocol', reserved='\x00\x00\x00\x00\x00\x00\x00\x00', peer_id=MY_PEER_ID):
        self.peer = peer
        self.pstr = pstr
        self.pstrlen = chr(len(self.pstr))
        self.reserved = reserved
        self.info_hash = peer.info_hash
        self.peer_id = MY_PEER_ID
        self.handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id
        #self.expected_return_peer_id = peer.peer_id
        #TODO verify that the return handshake's info_hash and peer_id are accurate

class Message(object):
    #deal with keep-alive message type

    def __init__(self, message, peer):
        message_types = {0: 'choke', 1: 'unchoke', 2: 'interested', 3: 'not interested',
                         4: 'have', 5: 'bitfield', 6: 'request', 7: 'piece', 8: 'cancel', 9: 'port'}
        self.message = message
        # self.peer_id = peer.peer_id
        self.info_hash = peer.info_hash
        if not message:
            self.message_type = 'keep-alive'
        else:
            self.message_type = message_types[self.message[4]]
        self.message_len = ord(self.message[:4]) #this might not be right
        self.payload = self.message[5:]

    #work out getting incomplete messages and buffering

def get_data(peer):
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PeerClientFactory(d, peer)
    reactor.connectTCP(peer.ip, peer.port, factory)
    print 'attempting to connect to ' + peer.ip + ':' + str(peer.port)
    return d

def got_data(data):
    print 'got data ' + data
    if data[1:20] == 'BitTorrent protocol':
        print 'its a handshake'
        received_handshake = Handshake(peer, reserved=data[20:28], peer_id=data[48:]) #need info_hash and peer_id checking
        print 'got the handshake' + received_handshake.handshake
        messages.append(received_handshake)
    else:
        print 'its a message'
        received_message = Message(data, peer)
        messages.append(received_message)



def main(peers):
    
    from twisted.internet import reactor
    
    messages = []
    errors = []



            #what to do with the message/handshake after receiving it
            
        # data.append(data)
        # print Message(data)
        #return Message(data)

    # def parse_handshake(data):
    #     print 'in parse_handshake'
    #     if data[1:20] == 'BitTorrent protocol':
    #         print 'parsing the handshake'
    #         received_handshake = Handshake(peer, reserved=data[20:28], info_hash=data[28:48], peer_id=data[48:])
    #         print 'got the handshake: ' + received_handshake.handshake
    #         return data

    #     else:
    #         return data

    def data_failed(err):
        errors.append(err)

    # def data_done():
    #     if len(data) + len(errors) == len(peers):
    #     # if data:
    #         reactor.stop()

    for peer in peers:
        #ip, port = peer.ip, peer.port
        # print peer.ip
        # print peer.port
        d = get_data(peer)
        if d:
            # d.addCallback(parse_handshake)

            d.addCallbacks(got_data, data_failed)
            # d.addBoth(data_done)

    reactor.run()
    # for data in data:
    #     print data
    # import pdb
    # pdb.set_trace()

torrent = TorrentFile('torrents/flagfromserver.torrent')
main(torrent.peers)


#When I receive a handshake, i want to make a handshake object from that and check that peer_id and info_hash
# are what they should be.
#Then, when I receive a message, I want to make a Message object and then choose what to do with that message
# using Message.message_type.
#I'm having trouble with getting the callbacks behaving correctly (line ~168) to do this. Do I need to do something
# with the dataReceived interface in the peer protocol?

# import pdb
# pdb.set_trace()