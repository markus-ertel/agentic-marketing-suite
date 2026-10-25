"""Offline structure checks for the eight modules inside the suite; reads files only."""
import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULES={'marketing':'.marketing','pr':'.pr','social-media':'.social-media','website':'.nocms','advertising':'.advertising','creative':'.creative','noCRM':'.nocrm','analytics':'.analytics'}
RULES={'noCRM':'REGELN.md'}
PLACEHOLDER=set('<>*…{')
class TestModuleStructure(unittest.TestCase):
 def test_core_files(self):
  for m,s in MODULES.items():
   with self.subTest(module=m):
    sysdir=ROOT/m/s
    self.assertTrue((ROOT/m/'AGENT.md').is_file())
    for name in ('STATE.md','LOG.md'):self.assertTrue((sysdir/name).is_file(),name)
    # website führt die Historie als Verzeichnis mit Register
    self.assertTrue((sysdir/'HISTORY.md').is_file() or (sysdir/'HISTORY'/'README.md').is_file(),'history')
 def test_rules_reference_suite(self):
  for m,s in MODULES.items():
   with self.subTest(module=m):
    text=(ROOT/m/s/RULES.get(m,'RULES.md')).read_text(encoding='utf8')
    self.assertIn('Gemeinsame Suite-Mindeststandards',text)
    self.assertIn('../.suite/GOVERNANCE.md',text)
 def test_internal_refs_resolve(self):
  for m,s in MODULES.items():
   with self.subTest(module=m):
    missing=set()
    for p in (ROOT/m).rglob('*.md'):
     for ref in re.findall(r'`('+re.escape(s)+r'/[^`\s]+)`',p.read_text(encoding='utf8')):
      if PLACEHOLDER&set(ref):continue
      if not (ROOT/m/ref.rstrip('/')).exists():missing.add(ref)
    self.assertEqual(sorted(missing),[])
 def test_neighbour_refs_are_modules(self):
  for m in MODULES:
   with self.subTest(module=m):
    # nur Modulordner-relative Verweise (`../name/`), keine dateirelativen Ketten wie `../../REGELN.md`
    # dateirelative Links auf vorhandene Ordner (z. B. ../digital/ innerhalb von methoden/) sind zulässig
    bad=set()
    for p in (ROOT/m).rglob('*.md'):
     for r in re.findall(r'(?<![./\w])\.\./(\.?[A-Za-z][\w-]*)/',p.read_text(encoding='utf8')):
      if r not in MODULES and r!='.suite' and not (p.parent.parent/r).is_dir():bad.add(r)
    self.assertEqual(sorted(bad),[])
 def test_website_skeleton(self):
  w=ROOT/'website'
  # archiv/inputs/ und archiv/releases/ entstehen erst im Betrieb und sind per .gitignore ausgeschlossen
  for d in ('input','archiv','.nocms/HISTORY','.nocms/KNOWLEDGE'):
   self.assertTrue((w/d).is_dir(),d)
  self.assertTrue((w/'.nocms'/'KNOWLEDGE'/'README.md').is_file())
  agent=(w/'AGENT.md').read_text(encoding='utf8')
  self.assertIn('\nwebsite/ ',agent)
  self.assertNotIn('\nprojekt/\n',agent)
  self.assertFalse((w/'site').exists(),'site/ entsteht erst mit Umsetzungsauftrag')
if __name__=='__main__':unittest.main()
