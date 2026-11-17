#!/usr/bin/env python3
import json,unittest,copy,importlib.util,xml.etree.ElementTree as ET
from pathlib import Path
base=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,base/'tools'/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
pf=load('creative_preflight');sp=load('svg_proof')
job=json.loads((base/'beispiele'/'demo-creative-job.json').read_text(encoding='utf-8'))
class TestCreative(unittest.TestCase):
    def test_demo_is_structurally_valid_but_not_print_ready(self):
        r=pf.check(job);self.assertTrue(r['ok']);self.assertFalse(r['print_ready_claim']);self.assertTrue(r['warnings'])
    def test_no_approval_without_evidence(self):
        bad=copy.deepcopy(job);bad['status']='released';r=pf.check(bad)
        self.assertFalse(r['ok']);self.assertTrue(any('Freigabe' in s or 'Printfreigabe' in s for s in r['blockers']))
    def test_negative_bleed_is_blocker(self):
        bad=copy.deepcopy(job);bad['print_spec']['bleed_mm']=-3;self.assertFalse(pf.check(bad)['ok'])
    def test_svg_valid(self):
        ET.fromstring(sp.make(job))
    def test_svg_rejects_absurd_format(self):
        bad=copy.deepcopy(job);bad['print_spec']['trim_width_mm']=99999
        with self.assertRaises(ValueError):sp.make(bad)
    def test_outputs_stay_inside_working_directory_and_never_overwrite(self):
        import os,tempfile
        with tempfile.TemporaryDirectory() as d:
            old=os.getcwd();os.chdir(d)
            try:
                sp.write_new_text('proofs/a.svg','x');self.assertEqual(Path(d,'proofs/a.svg').read_text(),'x')
                for bad in ('proofs/a.svg','../escape.svg',str(Path(d).parent/'abs.svg')):
                    with self.subTest(bad=bad),self.assertRaises(ValueError):sp.write_new_text(bad,'y')
                Path(d,'link').symlink_to(Path(d).parent)
                with self.assertRaises(ValueError):pf.write_new_text('link/x.json','y')
            finally:os.chdir(old)
    def test_svg_has_no_pdfx_claim(self):
        self.assertIn('NOT PRINT READY',sp.make(job))
if __name__=='__main__':unittest.main()
