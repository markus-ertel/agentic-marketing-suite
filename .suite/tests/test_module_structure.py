"""Offline structure checks for the nine modules inside the suite; reads files only."""
import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULES={'marketing':'.marketing','pr':'.pr','social-media':'.social-media','website':'.nocms','advertising':'.advertising','creative':'.creative','noCRM':'.nocrm','analytics':'.analytics','e-commerce':'.e-commerce'}
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
 def test_contract_module_enums(self):
  # Schema-Enums, Modulregister und Prüfskript kennen dieselben Module
  import json
  c=ROOT/'.suite'/'contracts'
  wo=json.loads((c/'work-order.schema.json').read_text(encoding='utf8'))['properties']
  art=json.loads((c/'artifact.schema.json').read_text(encoding='utf8'))['properties']
  for enum in (wo['lead_module']['enum'],wo['supporting_modules']['items']['enum'],art['owner_module']['enum']):
   self.assertEqual(sorted(enum),sorted(MODULES))
  register=(ROOT/'.suite'/'MODULES.md').read_text(encoding='utf8')
  check=(ROOT/'.suite'/'tools'/'check_repository.py').read_text(encoding='utf8')
  for m,s in MODULES.items():
   self.assertIn(f'| {m}/ |',register)
   self.assertIn(f"'{m}': '{s}'",check)
 def test_ecommerce_skeleton(self):
  e=ROOT/'e-commerce'
  for d in ('input','archiv'):self.assertTrue((e/d/'.gitkeep').is_file(),d)
  for name in ('RULES.md','BERATUNG.md','METHODEN.md','ARCHITECTURE.md','STRUKTUR.md','STATE.md','LOG.md','HISTORY.md','TESTFAELLE.md','QUELLEN.md','RECHT.md','AKTIONEN.md','FORMATE.md'):
   self.assertTrue((e/'.e-commerce'/name).is_file(),name)
  agent=(e/'AGENT.md').read_text(encoding='utf8')
  self.assertIn('„Wobei kann ich Ihnen bei Ihrem Online-Shop helfen?“',agent)
  # Beratungsmodul, keine Shop-Laufzeit und keine Ergebnisordner im Auslieferungszustand
  for d in ('shop','checkout','feeds','katalog','funnels'):self.assertFalse((e/d).exists(),d)
if __name__=='__main__':unittest.main()
