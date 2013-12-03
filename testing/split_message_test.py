import unittest
import message
import struct
import random

class TestSequenceFunctions(unittest.TestCase):
    def test_multiple_messages(self):
        pieces = [message.generate_message('piece', index=i, begin=0, block=struct.pack('>i', i)*2**8) for i in range(3)]
        buff = ''.join(p.bytes for p in pieces)
        messages, buff = message.Message.split_message(buff, 'x'*20)
        self.assertTrue(messages, pieces)

    def test_partial_messages(self):
        piece = message.generate_message('piece', index=0, begin=0, block=struct.pack('>i', 1)*2**8)
        partial1 = piece.bytes[:piece.message_len/3]
        partial2 = piece.bytes[piece.message_len/3:]
        buff = partial1
        messages, buff = message.Message.split_message(buff, 'x'*20)
         #receive 2nd message
        buff += partial2
        messages, buff = message.Message.split_message(buff, 'x'*20)
        self.assertTrue(messages, [piece])

    def test_garbage(self):
        ints = range(100)
        random.shuffle(ints)
        garbage = ''.join(struct.pack('>i', x) for x in ints)
        buff = garbage
        messages, buff = message.Message.split_message(buff, 'x'*20)
        print messages



if __name__ == '__main__':
    unittest.main()