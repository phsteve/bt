# class Handshake(object):
#     # should this inherit from Message?
#     def __init__(self, peer, pstr='', pstrlen='', reserved='', info_hash='', peer_id=''):
#         self.peer = peer
#         self.pstr = pstr or 'BitTorrent protocol'
#         self.pstrlen = chr(pstrlen) or chr(len(self.pstr))
#         self.reserved = reserved or '\x00\x00\x00\x00\x00\x00\x00\x00'
#         self.info_hash = info_hash or peer.info_hash
#         self.peer_id = peer_id or MY_PEER_ID
#         self.handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id

# my_handshake = Handshake()
# print my_handshake.handshake

# def parse_handshake(datum):
#     if datum[1:20] == 'BitTorrent protocol':
#         received_handshake = Handshake(peer, reserved=datum[20:28], info_hash=datum[28:48], peer_id=datum[48:])
#         print 'got the handshake: ' + received_handshake.handshake
#     else:
#         pass

import message
import bt

req = message.generate_message('request', index=2, begin=0, length=2**14)
import pdb
pdb.set_trace()