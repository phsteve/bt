import struct
import message
import random
import unittest
import bt
import StringIO

class TestSequenceFunctions(unittest.TestCase):
    def test_piece(self):
        # '''<len=0009+X><id=7><index><begin><block>'''
        buff = StringIO.StringIO()
        torrent = bt.TorrentFile('torrents/flagfromserver.torrent')
        controller = bt.Controller(torrent, buff)
        for i in range(20):
            piece = message.generate_message('piece', index=i, begin=0, block=struct.pack('>i', i)*(2**8))
            controller.piece_handler(piece)
        # print 'buffer value: ' + repr(buff.getvalue())

        # self.assertEquals(len(buff.getvalue()), 2**17)
        expected_result = ''.join([struct.pack('>i', i)*2**8 for i in range(20)])
        self.assertEquals(buff.getvalue(), expected_result)

    def test_piece_random(self):
        # '''<len=0009+X><id=7><index><begin><block>'''
        buff = StringIO.StringIO()
        torrent = bt.TorrentFile('torrents/flagfromserver.torrent')
        controller = bt.Controller(torrent, buff)
        indices = range(20)
        random.shuffle(indices)
        for i in indices:
            piece = message.generate_message('piece', index=i, begin=0, block=struct.pack('>i', i)*(2**8))
            controller.piece_handler(piece)
        # print 'buffer value: ' + repr(buff.getvalue())

        # self.assertEquals(len(buff.getvalue()), 2**17)
        expected_result = ''.join([struct.pack('>i', i)*2**8 for i in range(20)])
        self.assertEquals(buff.getvalue(), expected_result)


if __name__ == '__main__':
    unittest.main()