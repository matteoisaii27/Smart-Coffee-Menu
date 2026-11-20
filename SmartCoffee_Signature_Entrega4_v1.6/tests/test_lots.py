import unittest, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import next_lot_code
class LotTests(unittest.TestCase):
    def test_next_id_from_existing(self):
        with patch('app.read',return_value={'last':14}):
            self.assertEqual(next_lot_code([{'lot':'LOT-012'},{'lot':'lot-014'}]),'LOT-015')
    def test_sequence_never_reused(self):
        with patch('app.read',return_value={'last':32}):
            self.assertEqual(next_lot_code([{'lot':'LOT-003'}]),'LOT-033')
if __name__=='__main__': unittest.main()
