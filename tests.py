import unittest
import csviati

class TestSequenceFunctions(unittest.TestCase):
    def setUp(self):
        pass

    def test_save_file_file_fails(self):
        self.assertRaises(csviati.Error, csviati.save_file, 'file:///etc/passwd', 'csv', '.')

if __name__ == '__main__':
    unittest.main()
