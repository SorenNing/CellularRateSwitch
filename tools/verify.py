"""Read-only package verification. No installation or payload execution."""
from pathlib import Path
import io,tarfile,json,hashlib,plistlib,sys
from macho import inspect
from helper_invariants import compare_helper
from binary_checks import require
ROOT=Path(__file__).resolve().parents[1]
def verify(p):
 b=p.read_bytes();require(b[:8]==b'!<arch>\n','ar magic');q=8;members={}
 while q<len(b):
  h=b[q:q+60];require(len(h)==60 and h[58:]==b'`\n','ar header');n=h[:16].decode().strip().rstrip('/');s=int(h[48:58]);q+=60;require(n not in members and q+s<=len(b),'ar bounds');members[n]=b[q:q+s];q+=s+s%2
 require(q==len(b) and set(members)=={'debian-binary','control.tar.gz','data.tar.gz'} and members['debian-binary']==b'2.0\n','deb layout')
 def read_tar(data):
  files={};dirs=set()
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as t:
   for m in t:
    n=m.name.removeprefix('./');require(not Path(n).is_absolute() and '..' not in Path(n).parts and m.uid==m.gid==0 and not m.pax_headers,'tar metadata')
    if m.isdir():dirs.add(n);require(m.mode==0o755,'directory mode');continue
    require(m.isfile() and n not in files,'nonregular/duplicate');files[n]=(t.extractfile(m).read(),m.mode)
  for n in files:
   for d in Path(n).parents:
    if str(d)!='.':require(str(d) in dirs,'missing parent '+str(d))
  return files
 ctrl=read_tar(members['control.tar.gz']);require(set(ctrl)=={'control','md5sums'},'maintainer script not permitted')
 fields=dict(s.split(': ',1) for s in ctrl['control'][0].decode().splitlines());arch=fields['Architecture'];require(arch in ('iphoneos-arm64','iphoneos-arm64e'),'arch')
 require(fields['Package']=='com.ning.cellularrate' and fields['Version']=='1.0.0','identity')
 prefix='var/jb/' if arch=='iphoneos-arm64' else '';sub=0 if prefix else 0x80000002
 files=read_tar(members['data.tar.gz']);hashes={}
 for line in ctrl['md5sums'][0].decode().splitlines():
  digest,n=line.split('  ',1);hashes[n]=digest
 require(set(hashes)==set(files),'md5 manifest files')
 binaries={};backend_count=helper_count=main_count=bridge_count=0
 for n,(data,mode) in files.items():
  require(hashlib.md5(data).hexdigest()==hashes[n],'md5 mismatch')
  require(n.startswith(prefix+'Library/ControlCenter/Bundles/NingCellularRate.bundle/') or n.startswith(prefix+'usr/'),'foreign path '+n)
  if prefix:require(n.startswith(prefix),'rootless leak')
  if data[:4] in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):
   require(mode==0o755,'binary permissions');r=inspect(data);binaries[n]=r
   if n.endswith('/NingCellularRate'):inspect(data,sub);main_count+=1
   elif n.endswith('/RateBackend'):
    inspect(data,sub);backend_count+=1;require(b'CCCellularRate' not in data and b'NNCellularRateModuleViewController' in data,'namespace isolation');require(all('@loader_path/RateSpawnBridge.dylib' in s['loads'] for s in r['slices']),'private bridge dependency')
   elif n.endswith('/RateSpawnBridge.dylib'):inspect(data,sub);bridge_count+=1
   elif n.endswith('/NingCellularRateTool'):
    helper_count+=1;require(all({5,7}.issubset(x['signature']['slots']) for x in r['slices']),'helper entitlements');r['preserved_original']=compare_helper((ROOT/'Vendor/CCCellularRateTool').read_bytes(),data)
   else:raise ValueError('Unexpected binary '+n)
  else:require(mode==0o644,'resource permissions')
 require(main_count==backend_count==helper_count==bridge_count==1,'missing or duplicate program')
 base=prefix+'Library/ControlCenter/Bundles/NingCellularRate.bundle/'
 info=plistlib.loads(files[base+'Info.plist'][0]);require(info['CFBundleIdentifier']=='com.ning.cellularrate.module' and info['NSPrincipalClass']=='NINGCRModule','module registration')
 return {'file':p.name,'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'control':fields,'files':len(files),'binaries':binaries,'runtime_tested':False}
if __name__=='__main__':
 paths=[Path(s) for s in sys.argv[1:]] or sorted((ROOT/'dist').glob('*.deb'));require(paths,'no deb files')
 reports=[verify(p) for p in paths];out=ROOT/'dist/package-validation.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
 for r in reports:print('VERIFIED',r['file'],r['size'],r['sha256'])
