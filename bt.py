from bencode import bencode, bdecode
import requests
import struct
import bitstring
from hashlib import sha1
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.task import LoopingCall
import sys
import os
from copy import copy


from message import Message, generate_message, DiffRequest, KeepAlive

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
        self.big_pieces = self.torrent.piece_length > 2**14 #flag for handling pieces longer than 2**14
        self.piece_ratio = (self.torrent.piece_length - 1) / 2**14 + 1
        self.pieces_requested = bitstring.BitArray('0b' + self.torrent.num_pieces * '0')#{piece_index: [done?, [(begin, end) for each chunk received]]}
        self.pieces_completed = bitstring.BitArray('0b' + self.torrent.num_pieces * '0')
        self.blocks_requested = [bitstring.BitArray('0b' + self.piece_ratio * '0') for _ in xrange(self.torrent.num_pieces)]
        self.blocks_completed = [bitstring.BitArray('0b' + self.piece_ratio * '0') for _ in xrange(self.torrent.num_pieces)] #List of bitfields, each sublist is the beginning and end of 
        num_blocks_in_last_piece = 1 + (self.torrent.file_length - (self.torrent.num_pieces-1)*self.torrent.piece_length) / 2**14
                                    #length of last piece / block_length
        self.blocks_requested[-1] = bitstring.BitArray('0b' + '0' * num_blocks_in_last_piece)
        self.blocks_completed[-1] = bitstring.BitArray('0b' + '0' * num_blocks_in_last_piece)
        self.outstanding_pieces = ''
        self.outstanding_blocks = ''

    @staticmethod
    def get_outstanding_blocks(blocks_completed, blocks_requested):
        #return list of bitstrings that have been requested but not downloaded
        return [comp ^ req for comp, req in zip(blocks_completed, blocks_requested)]

    @staticmethod
    def get_outstanding_pieces(pieces_completed, pieces_requested):
        return pieces_completed ^ pieces_requested

    def set_outstanding_blocks(self):
        self.outstanding_blocks = self.get_outstanding_blocks(self.blocks_completed, self.blocks_requested)
        self.outstanding_pieces = self.get_outstanding_pieces(self.pieces_completed, self.pieces_requested)

    @staticmethod
    def reset_blocks_requested(blocks_completed, blocks_requested):
        result = [((req & completed) | outstanding) for req, completed, outstanding in zip(blocks_requested, blocks_completed, Controller.get_outstanding_blocks(blocks_completed, blocks_requested))]
        # print 'new blocks: ' + '\n'.join(r.bin for r in result)
        return result

    @staticmethod
    def reset_pieces_requested(pieces_completed, pieces_requested):
        result = (pieces_requested & pieces_completed) | Controller.get_outstanding_pieces(pieces_completed, pieces_requested)
        # print 'new pieces: ' + result.bin
        return result

    def reset_blocks(self):
        # print 20* '*\n' + "resetting blocks" + 20*'*\n'
        # print [b.bin for b in self.blocks_requested]
        # print self.pieces_requested.bin
        # # self.blocks_requested = self.reset_blocks_requested(self.blocks_completed, self.blocks_requested)
        # # self.pieces_requested = self.reset_pieces_requested(self.pieces_completed, self.pieces_requested)
        # print 'new blocks: '
        # # for i in range(len(self.pieces_requested.bin)):
        # #     if self.pieces_requested.bin[i] == '0':
        # #         print self.blocks_requested[i].bin
        self.blocks_requested = self.blocks_completed[:]
        self.pieces_requested = copy(self.pieces_completed)
        # # import pdb
        # # pdb.set_trace()
        # print [b.bin for b in self.blocks_requested]
        # print self.pieces_requested.bin
        # pass

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
        if self.peer_dict[message.peer_id].has_pieces == '0':
            self.peer_dict[message.peer_id].has_pieces = bitstring.BitArray('0b' + '0' * self.torrent.num_pieces)
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
        print "received piece #%s begin @ %s from %s" %(piece.index, piece.begin, self.peer_dict[piece.peer_id].ip)

        
        self.blocks_completed[piece.index].overwrite('0b1', piece.begin/(2**14))
        # print 'blocks completed: ' + self.blocks_completed[piece.index].bin
        # self.block_buffer[piece.index].append(piece)
        if '0' not in self.blocks_completed[piece.index].bin:
        #     self.check_hash(piece.index)
            # print 'Finished downloading piece #%d' %piece.index
            self.pieces_completed.overwrite('0b1', piece.index)
            print 'pieces completed: %s' % self.pieces_completed.bin
            # print 'pieces_completed: %s'%self.pieces_completed.bin
        self.received_file.seek(self.torrent.piece_length * piece.index + piece.begin)

        self.received_file.write(piece.block)


        if '0' not in self.pieces_completed.bin[:self.torrent.num_pieces]:
            print 'Done!'

            from twisted.internet import reactor
            reactor.stop()
            if self.torrent.mode == 'multi':
                if not os.path.exists(self.torrent.name):
                    os.mkdir(self.torrent.name)
                os.chdir(self.torrent.name)
                self.split_file(self.torrent.files, self.received_file)



    def cancel_handler(self, message):
        pass

    def port_handler(self, message):
        pass

    def check_hash(self, bytes, index):
        # print self.torrent.piece_hashes[piece.index]
        expected = struct.unpack('20s', self.torrent.piece_hashes[index])[0]
        got = sha1(bytes).digest()
        # import pdb
        # pdb.set_trace()
        if expected != got:
            print 'received a bad piece!'
            print 'expected ', expected
            print 'got ', got
            # 
            # self.peer_dict[piece.peer_id]
        else:
            print 'piece checked OK'

    def get_next_block(self):
        #usual, non-end values for index, begin, length
        index = self.pieces_requested.bin.find('0')
        if index > -1:
            begin = self.blocks_requested[index].bin.find('0') * 2**14
            if (index == self.torrent.num_pieces - 1) and ('0' not in self.blocks_requested[index].bin[:-1]):
                # print 'last block of last piece'
                #last block of last piece
                length = self.get_last_block_length_of_last_piece(index)
            elif index >= 0 and '0' not in self.blocks_requested[index].bin[:-1]:
                # print 'last block of normal piece'
                length = self.get_last_block_length(index)
            else:
                # print 'normal block'
                length = 2**14

            return {'index': index, 'begin': begin, 'length': length}

    def re_request_blocks(self):
        index = self.outstanding_pieces.bin.find('1')
        if index > -1:
            begin = self.outstanding_blocks[index].bin.find('1') * 2**14
            if (index == self.torrent.num_pieces - 1) and ('1' not in self.outstanding_blocks[index].bin[:-1]):
                # print 'last block of last piece'
                #last block of last piece
                length = self.get_last_block_length_of_last_piece(index)
            elif index >= 0 and '1' not in self.outstanding_blocks[index].bin[:-1]:
                # print 'last block of normal piece'
                length = self.get_last_block_length(index)
            else:
                # print 'normal block'
                length = 2**14

            return {'index': index, 'begin': begin, 'length': length}

    def get_last_block_length(self, index):
        length = self.torrent.piece_length - (len(self.blocks_requested[index].bin)-1)*(2**14)
        return length

    def get_last_block_length_of_last_piece(self, index):
        length = (self.torrent.file_length - (self.torrent.piece_length * (self.torrent.num_pieces - 1))) \
                 - ((len(self.blocks_requested[index].bin) - 1) * 2**14)
        return length

    def send_control_message(self, type, peer_id):
        # sends a message (either choke, unchoke, interested, or not interested) to a peer
        msg = generate_message(type, peer_id=peer_id)
        self.peer_dict[peer_id].factory.transport.write(msg.bytes)

    @staticmethod
    def split_file(file_paths, file_to_split):
        for file_path in file_paths:
            if len(file_path['path']) > 1:
                path = '/'.join(file_path['path'][:-1])
                # filename = file_path['path'][-1]
                entire_path = '/'.join(file_path['path'])
                if not os.path.exists(path):
                    os.makedirs(path)
            else:
                entire_path = file_path['path'][0]
            f = open(entire_path, 'w+b')
            # import pdb
            # pdb.set_trace()
            # self.received_file.seek(seek_to)
            f.write(file_to_split.read(file_path['length']))
            f.close()





class TorrentFile(object):
    def __init__(self, filepath):
        self.f = open(filepath, 'rb').read()
        self.decoded = bdecode(self.f)
        self.info = self.decoded['info']
        self.piece_length = self.info['piece length']
        self.pieces = self.info['pieces']
        self.name = self.info['name']
        self.info_hash = sha1(bencode(self.decoded['info'])).digest()
        self.num_pieces = len(self.pieces)/20
        self.announce_url = self.decoded['announce']
        self.piece_hashes = [self.pieces[i:20+i] for i in range(0, len(self.pieces), 20)]
        if 'length' in self.info:
            #single file mode
            self.mode = 'single'
            self.file_length = self.info['length']
        if 'files' in self.info:
            #multi file mode
            self.mode = 'multi'
            self.files = self.info['files']
            self.file_lengths = [f['length'] for f in self.files]
            self.file_length = sum(self.file_lengths)
            # self.file_paths = [f for f in self.files]
            # '/'.join([f['path'] for f in self.files])
        # if 'files' in self.decoded:
        #     import pdb
        #     pdb.set_trace()

class TrackerResponse(object):
    def __init__(self, torrent):
        self.torrent = torrent
        self.request_payload = {'info_hash': torrent.info_hash,
                                'peer_id': MY_PEER_ID,
                                'port': 6881,
                                'uploaded': 0,
                                'downloaded': 0,
                                'left': self.torrent.file_length,
                                'compact': 1,
                                'event': 'started',
                                'numwant': 80,
                                'supportcrypto': 0,
                                'requirecrypto': 0
                                }
        self.peers_str = self.req_peers_from_tracker(torrent)
        self.peers = [Peer(peer_str, self.request_payload['info_hash']) for peer_str in self.peers_str]
        # make a dictionary of peer_id:peer pairs
    
    def req_peers_from_tracker(self, torrent):
        print 'requesting peers'
        resp = requests.get(torrent.announce_url, params=self.request_payload)
        response = bdecode(resp.content)
        # import pdb
        # pdb.set_trace()
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
        self.protocol = None
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.handshake = handshake
        self.has_pieces = '0'
        self.status = status # status is 4-item dict, values of am_choking, am_interested, peer_choking, peer_interested
        # self.messages_received = []
        # self.payload = payload

    def parse_peer_str(self, peer_str):
        ip = '.'.join(str(ord(char)) for char in peer_str[:4])
        port = 256*ord(peer_str[-2]) + ord(peer_str[-1])
        return ip, port

    def connect(self, controller):
        print 'attempting to connect to ' + self.ip + ':' + str(self.port)
        from twisted.internet import reactor
        self.factory = PeerClientFactory(self, controller)
        reactor.connectTCP(self.ip, self.port, self.factory)

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
        print 'connection made to ' + self.factory.peer.ip
        sent_handshake = Handshake(self.controller.info_hash).handshake
        self.transport.write(sent_handshake)
        lc = LoopingCall(self.send_keepalive)
        lc.start(90)


    def send_keepalive(self):
        msg = KeepAlive()
        self.transport.write(msg.bytes)

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
        # self.controller.peer_dict[peer_id].protocol = self
        self.controller.add_peer(self.factory.peer)
        self.shook_hands = True
        self.controller.peer_dict[peer_id].handshake = received_handshake
        print 'handshake received from: %r' %self.transport.getPeer()
    
        inter = generate_message('interested')
        print 'sent an interested to %r' %(self.transport.getPeer())
        self.transport.write(inter.bytes)
        self.controller.peer_dict[peer_id].status['am_interested'] = 1
        buff = buff[68:]
        messages, buff = Message.split_message(buff, peer_id)
        return messages, buff
        

    def dataReceived(self, bytes):
        messages = []
        self._buffer += bytes
        
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
                # print 'received a %s from %s' %(message.type, self.transport.getPeer())
                
                self.controller.handle(message)


            
            block = self.controller.get_next_block()
            #TODO: split into three functions
            if block:
                req = DiffRequest(block['index'], block['begin'], block['length'])
                self.transport.write(req.bytes)
                print 'sent req for index %d and begin %d with length %d to %r' %(req.index, req.begin, req.length, self.transport.getPeer())
                
                self.controller.blocks_requested[block['index']].overwrite('0b1', block['begin']/(2**14))
                if '0' not in self.controller.blocks_requested[block['index']].bin:
                    self.controller.pieces_requested.overwrite('0b1', block['index'])

            else:
                block = self.controller.re_request_blocks()
                if block:
                    req = DiffRequest(block['index'], block['begin'], block['length'])
                    self.transport.write(req.bytes)
                    print 'sent req for index %d and begin %d with length %d to %r' %(req.index, req.begin, req.length, self.transport.getPeer())
                    
                    self.controller.outstanding_blocks[block['index']].overwrite('0b0', block['begin']/(2**14))
                    if '1' not in self.controller.outstanding_blocks[block['index']].bin:
                        self.controller.outstanding_pieces.overwrite('0b0', block['index'])

    def connectionLost(self, reason):
        print 'connection lost from: ' + self.factory.peer.ip

class PeerClientFactory(ClientFactory):
    protocol = PeerProtocol

    def __init__(self, peer, controller):
        self.peer = peer
        self.controller = controller

    def buildProtocol(self, addr):
        return PeerProtocol(self, self.controller)

    def clientConnectionFailed(self, connector, reason):
        print self.peer.ip, ' Failed: ', reason,



def main():
    # import pdb
    # pdb.set_trace()
    try:
        filepath = sys.argv[1]
        torrent = TorrentFile(filepath)
    except Exception as err:
        sys.exit('Please enter a valid file path to a valid torrent, error: %s'%err)

    if torrent.mode == 'single':
        received_file = open(torrent.name, 'w+b')
    elif torrent.mode == 'multi':
        received_file = open('temp', 'w+b')

    controller = Controller(torrent, received_file)
    tracker_response = TrackerResponse(torrent)
    peers = tracker_response.peers
    # import pdb
    # pdb.set_trace()
    #this needs to be changed to update when the controller gets new peers from the tracker
    for peer in peers:
        if peer.port != 0:
            peer.connect(controller)
    
    lc1 = LoopingCall(controller.set_outstanding_blocks)
    lc1.start(30)

    from twisted.internet import reactor
    reactor.run()





if __name__ == '__main__':
    main()


