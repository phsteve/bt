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
        self.peers = self.req_peers_from_tracker()
        self.peer_list = [Peer(peer_str) for peer_str in self.peers]

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

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = str(256*ord(peer_str[-2]) + ord(peer_str[-1]))
        return ip, port




torrent = TorrentFile('torrents/flagfromserver.torrent')

import pdb
pdb.set_trace()