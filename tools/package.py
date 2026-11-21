"""Deterministic deb writer: explicit directory entries and modes, no ar tool."""
from pathlib import Path
import io,tarfile,gzip,hashlib,json,plistlib,sys
ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0'
BUNDLE='Library/ControlCenter/Bundles/NingCellularRate.bundle'
def sha(b):return hashlib.sha256(b).hexdigest()
def tar_bytes(files):
 dirs={'.'}
 for n in files:
  p=Path(n).parent
  while p.as_posix()!='.':dirs.add(p.as_posix());p=p.parent
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as t:
  for n in sorted(dirs,key=lambda x:(len(Path(x).parts),x)):
   m=tarfile.TarInfo(n);m.type=tarfile.DIRTYPE;m.mode=0o755;m.uid=m.gid=0;m.mtime=0;t.addfile(m)
  for n,(b,mode) in sorted(files.items()):
   m=tarfile.TarInfo(n);m.size=len(b);m.mode=mode;m.uid=m.gid=0;m.mtime=0;t.addfile(m,io.BytesIO(b))
 return gzip.compress(buf.getvalue(),compresslevel=9,mtime=0)
def deb_bytes(members):
 out=b'!<arch>\n'
 for n,b in members:
  h=f'{n+"/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(b):<10}`\n'.encode('ascii');assert len(h)==60
  out+=h+b+(b'\n' if len(b)%2 else b'')
 return out
def main():
 dist=ROOT/'dist';dist.mkdir(exist_ok=True);reports=[]
 for arch,cpu,prefix in [('iphoneos-arm64','arm64','var/jb/'),('iphoneos-arm64e','arm64e','')]:
  payload={}
  def put(n,b,mode=0o644):payload[prefix+n]=(b,mode)
  put(BUNDLE+'/NingCellularRate',(ROOT/f'build/{cpu}/NingCellularRate').read_bytes(),0o755)
  for p in sorted((ROOT/'Resources').rglob('*')):
   if p.is_file():put(BUNDLE+'/'+p.relative_to(ROOT/'Resources').as_posix(),p.read_bytes())
  # Build script stages the isolated, signed backend and helper per architecture.
  for p in sorted((ROOT/f'build/{cpu}/payload').rglob('*')):
   if p.is_file():
    n=p.relative_to(ROOT/f'build/{cpu}/payload').as_posix();put(n,p.read_bytes(),0o755 if p.name in ('RateBackend','NingCellularRateTool','RateSpawnBridge.dylib') else 0o644)
  icon=ROOT/'Resources/SettingsIcon@3x.png'
  if icon.exists():put('usr/share/icons/com.ning.cellularrate.png',icon.read_bytes())
  fields={'Package':'com.ning.cellularrate','Name':'蜂窝4/5G切换','Version':VERSION,'Architecture':arch,'Maintainer':'Ning&Netskao','Author':'Ning&Netskao','Section':'Tweaks','Priority':'optional','Depends':'firmware (>= 16.0), firmware (<< 18.0), com.opa334.ccsupport','Description':'Standalone Control Center 4G/5G switch with native state readback.','Icon':'file:///'+prefix+'usr/share/icons/com.ning.cellularrate.png'}
  control=('\n'.join(k+': '+v for k,v in fields.items())+'\n').encode()
  md5=('\n'.join(hashlib.md5(b).hexdigest()+'  '+n for n,(b,_) in sorted(payload.items()))+'\n').encode()
  data=deb_bytes([('debian-binary',b'2.0\n'),('control.tar.gz',tar_bytes({'control':(control,0o644),'md5sums':(md5,0o644)})),('data.tar.gz',tar_bytes(payload))])
  path=dist/f'com.ning.cellularrate_{VERSION}_{arch}.deb';path.write_bytes(data);reports.append({'file':path.name,'size':len(data),'sha256':sha(data),'files':len(payload),'architecture':arch})
 (dist/'packages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n');print(json.dumps(reports,ensure_ascii=False))
if __name__=='__main__':main()
