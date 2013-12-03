import unittest
import message
import struct


class TestSequenceFunctions(unittest.TestCase):
    def test_piece_generation(self):
        msg = message.generate_message('piece', index=0, begin=0, block=struct.pack('>i', 2)*(2**14))
        self.assertEquals(msg.index, 0)
        self.assertEquals(msg.message_len, 9+msg.block_len)
        self.assertEquals(msg.begin, 0)
        # print repr(msg.bytes)

if __name__ == '__main__':
    unittest.main()