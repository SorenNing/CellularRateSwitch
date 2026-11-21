"""Verify actual packaged executables on macOS; never execute package payloads."""
from pathlib import Path
import io,tarfile,subprocess,tempfile,json
ROOT=Path(__file__).resolve().parents[1]
report=[]
for package in sorted((ROOT/'dist').glob('*.deb')):
 data=package.read_bytes();q=8;payload=None
 while q<len(data):
  h=data[q:q+60];name=h[:16].decode().strip().rstrip('/');size=int(h[48:58]);q+=60
  if name=='data.tar.gz':payload=data[q:q+size]
  q+=size+size%2
 assert payload is not None
 with tempfile.TemporaryDirectory() as d:
  base=Path(d);programs=[]
  with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tar:
   for entry in tar:
    name=entry.name.removeprefix('./');assert not Path(name).is_absolute() and '..' not in Path(name).parts
    if not entry.isfile():continue
    target=base/name;target.parent.mkdir(parents=True,exist_ok=True);b=tar.extractfile(entry).read();target.write_bytes(b);target.chmod(entry.mode)
    if b[:4] in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):programs.append(target)
  for program in programs:
   r=subprocess.run(['codesign','--verify','--strict','--all-architectures',str(program)],capture_output=True,text=True)
   assert r.returncode==0,(program.name,r.stderr)
  for name in ('NingCellularRate.bundle','RateBackend.bundle'):
   bundles=list(base.rglob(name));assert len(bundles)==1
   assert (bundles[0]/'_CodeSignature/CodeResources').is_file(),name+' resource envelope missing'
   r=subprocess.run(['codesign','--verify','--strict','--deep',str(bundles[0])],capture_output=True,text=True);assert r.returncode==0,(name,r.stderr)
  report.append({'package':package.name,'programs':[str(p.relative_to(base)) for p in programs],'strict_codesign':True,'outer_and_backend_bundle_resources':True})
(ROOT/'dist/macos-final-signatures.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
