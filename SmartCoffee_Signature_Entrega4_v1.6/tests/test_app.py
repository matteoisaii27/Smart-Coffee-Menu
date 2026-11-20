import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import apriori, state, viable
from datetime import date,timedelta

class SmartCoffeeTests(unittest.TestCase):
    def test_apriori(self):
        t=[{'items':['Pan','Cafe']} for _ in range(8)]+[{'items':['Pan','Te']} for _ in range(2)]+[{'items':['Cafe','Galleta']} for _ in range(2)]
        rules=apriori(t,.15,.70,0.9)
        self.assertTrue(any(r['a']=='Pan' and r['b']=='Cafe' for r in rules))
    def test_expiry(self):
        def lot(d):return {'expiry':(date.today()+timedelta(days=d)).isoformat()}
        self.assertEqual(state(lot(-1)),'Vencido');self.assertEqual(state(lot(0)),'Crítico');self.assertEqual(state(lot(2)),'Crítico');self.assertEqual(state(lot(3)),'Próximo');self.assertEqual(state(lot(5)),'Próximo');self.assertEqual(state(lot(6)),'Vigente')
    def test_public_requires_approval_and_stock(self):
        today=date.today().isoformat();p={'status':'approved','expires':today,'products':['Pan','Cafe']}; inv=[{'product':x,'qty':3,'expiry':today} for x in ['Pan','Cafe']]
        self.assertTrue(viable(p,inv));p['status']='pending';self.assertFalse(viable(p,inv));p['status']='approved';inv[0]['qty']=0;self.assertFalse(viable(p,inv))
if __name__=='__main__': unittest.main()
