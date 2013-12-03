import unittest
import bt
import message

class TestSequenceFunctions(unittest.TestCase):
    def test_request(self):
        torrent = bt.TorrentFile('torrents/flagfromserver.torrent')
        received_file = open('testfile.jpg', 'rwb')
        controller = bt.Controller(torrent, received_file)

        incoming_request = message.generate_message('request', index=1, begin=0, length=2**14, peer_id='12345123451234512345')
        received_file.seek(torrent.piece_length * 1)

    
        # incoming_request = message.generate_message('request', index=1, begin=0, length=2**14, peer_id='12345123451234512345')
        # received_file.seek(torrent.piece_length * 1)
        # expected_sent_piece = message.generate_message('piece', bytes=received_file.seek(torrent.piece_length * 1).read(2**14))
        # print expected_sent_piece


if __name__ == '__main__':
    unittest.main()