import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('store',Path(__file__).parents[1]/'tools'/'contact_store.py')
store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
class StoreTests(unittest.TestCase):
    def test_init_creates_only_on_request(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse((Path(d)/'kontakte').exists())
            store.init(d)
            self.assertTrue((Path(d)/'kontakte/contacts.csv').exists())
    def test_add_keeps_one_contact(self):
        with tempfile.TemporaryDirectory() as d:
            store.init(d);store.add(d,'A-1','Test Beispiel')
            lines=(Path(d)/'kontakte/contacts.csv').read_text().splitlines()
            self.assertEqual(len(lines),2)
            with self.assertRaises(ValueError):store.add(d,'A-1','Doppelt')
    def test_formula_cells_are_neutralized(self):
        import csv
        with tempfile.TemporaryDirectory() as d:
            store.init(d);store.add(d,'A-1','=HYPERLINK("https://example.invalid","x")',organization='+cmd',email='@x')
            with open(Path(d)/'kontakte/contacts.csv',newline='') as f:row=list(csv.DictReader(f))[0]
            self.assertEqual(row['display_name'],"'=HYPERLINK(\"https://example.invalid\",\"x\")")
            self.assertEqual((row['organization'],row['email']),("'+cmd","'@x"))
            store.add(d,'A-2','Erika Beispiel');self.assertIn('Erika Beispiel',(Path(d)/'kontakte/contacts.csv').read_text())
            with self.assertRaises(ValueError):store.add(d,'=A-3','Formel-ID')
    def test_parallel_adds_keep_every_contact(self):
        import subprocess,sys
        tool=Path(__file__).parents[1]/'tools'/'contact_store.py'
        with tempfile.TemporaryDirectory() as d:
            store.init(d)
            procs=[subprocess.Popen([sys.executable,'-B',str(tool),'--root',d,'add-contact','--id','P-%d'%i,'--name','Fiktiv %d'%i],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for i in range(12)]
            self.assertEqual([p.wait() for p in procs],[0]*12)
            self.assertEqual(len((Path(d)/'kontakte/contacts.csv').read_text().splitlines()),13)
            self.assertFalse((Path(d)/'kontakte/contacts.csv.lock').exists())
    def test_no_auto_initialize_on_add(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):store.add(d,'A-1','Test')
if __name__=='__main__':unittest.main()
