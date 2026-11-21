"""Relocate backend without changing its original query/action instructions.
Equal-length class namespace rename; one import renamed and rebound to a private
adjacent dylib. No helper argv, rate value, or CoreTelephony ABI is guessed.
"""
from pathlib import Path
import struct,hashlib,json,sys,plistlib
ROOT=Path(__file__).resolve().parents[1]
EXPECTED='5ccbb7cf9f8b18959f8901c88a21ee3d63a280f9ebb8a24b6e272bbd40ee4e76'
OLD=b'_posix_spawn';NEW=b'_ning__spawn';assert len(OLD)==len(NEW)
def uleb(b,p):
 val=0;shift=0
 while True:
  x=b[p];p+=1;val|=(x&127)<<shift
  if x<128:return val,p
  shift+=7;assert shift<64

def patch(data):
 b=bytearray(data);assert b[:4]==b'\xcf\xfa\xed\xfe';n,cmdsz=struct.unpack_from('<II',b,16);p=32;libs=0;dyld=None;chain=None;sym=None
 for _ in range(n):
  c,z=struct.unpack_from('<II',b,p)
  if c in (0xc,0x80000018,0x8000001f,0x20,0x80000023):libs+=1
  if c in (0x22,0x80000022):dyld=struct.unpack_from('<10I',b,p+8)
  if c==0x80000034:chain=struct.unpack_from('<II',b,p+8)
  if c==2:sym=struct.unpack_from('<4I',b,p+8)
  p+=z
 ordinal=libs+1;assert ordinal<16
 name=b'@loader_path/RateSpawnBridge.dylib\0';size=(24+len(name)+7)&~7
 assert p==32+cmdsz and not any(b[p:p+size]),'no zero load-command slack'
 load=struct.pack('<6I',0xc,size,24,0,0,0)+name;load+=bytes(size-len(load));b[p:p+size]=load
 struct.pack_into('<II',b,16,n+1,cmdsz+size)
 changed=0
 if dyld:
  for off,length in ((dyld[2],dyld[3]),(dyld[6],dyld[7])):
   q=off;end=off+length;lastordinal=None;lastimm=None
   while q<end:
    at=q;op=b[q]&0xf0;imm=b[q]&15;q+=1
    if op==0x10:lastordinal=at;lastimm=imm
    elif op==0x20:_,q=uleb(b,q);lastordinal=None
    elif op==0x30:lastordinal=None
    elif op==0x40:
     endname=b.index(0,q);s=bytes(b[q:endname])
     if s==OLD:
      assert lastordinal is not None and lastimm==libs,'unexpected original spawn ordinal'
      b[lastordinal]=0x10|ordinal;b[q:endname]=NEW;changed+=1
     q=endname+1
    elif op in (0x60,0x70,0x80,0xa0):_,q=uleb(b,q)
    elif op==0xc0:_,q=uleb(b,q);_,q=uleb(b,q)
    elif op==0xd0:raise ValueError('threaded dyld bindings not handled')
    elif op not in (0x00,0x50,0x90,0xb0):raise ValueError('unknown bind opcode')
 if chain:
  off,length=chain;version,starts,imports,symbols,count,fmt,symfmt=struct.unpack_from('<7I',b,off);assert version==symfmt==0 and fmt in (1,2,3)
  width={1:4,2:8,3:16}[fmt]
  for i in range(count):
   q=off+imports+i*width
   if fmt in (1,2):v=struct.unpack_from('<I',b,q)[0];nm=v>>9;oldord=v&255
   else:v=struct.unpack_from('<Q',b,q)[0];nm=v>>32;oldord=v&65535
   s=off+symbols+nm;end=b.index(0,s)
   if bytes(b[s:end])==OLD:
    assert oldord==libs,'unexpected chained spawn ordinal';b[s:end]=NEW
    if fmt in (1,2):struct.pack_into('<I',b,q,(v&~255)|ordinal)
    else:struct.pack_into('<Q',b,q,(v&~65535)|ordinal)
    changed+=1
 assert changed==1,'expected exactly one loader import binding'
 symoff,count,stroff,strsize=sym;stchanges=0
 for i in range(count):
  q=symoff+16*i;idx=struct.unpack_from('<I',b,q)[0]
  if not idx:continue
  s=stroff+idx;end=b.index(0,s);value=bytes(b[s:end])
  if value in (OLD,NEW):
   # The chained import symbol pool may share the string table.
   desc=struct.unpack_from('<H',b,q+6)[0];assert (desc>>8)==libs
   struct.pack_into('<H',b,q+6,(desc&255)|(ordinal<<8));b[s:end]=NEW;stchanges+=1
 assert stchanges==1
 old=b'CCCellularRate';new=b'NNCellularRate';count=b.count(old);assert count>=3
 b=b.replace(old,new);assert old not in b
 return bytes(b),{'original_subtype':hex(struct.unpack_from('<I',data,8)[0]),'bridge_ordinal':ordinal,'class_tokens':count,'loader_imports_changed':changed,'symbol_table_imports_changed':stchanges,'original_sha256':hashlib.sha256(data).hexdigest(),'patched_unsigned_sha256':hashlib.sha256(b).hexdigest()}

def main():
 data=(ROOT/'Vendor/CCCellularRateModule').read_bytes();assert hashlib.sha256(data).hexdigest()==EXPECTED
 assert data[:4]==b'\xca\xfe\xba\xbe';report=[]
 for i in range(struct.unpack_from('>I',data,4)[0]):
  cpu,sub,off,size,align=struct.unpack_from('>5I',data,8+20*i);arch={0:'arm64',0x80000002:'arm64e'}[sub]
  patched,r=patch(data[off:off+size]);target=ROOT/f'build/{arch}/payload/Library/ControlCenter/Bundles/NingCellularRate.bundle/RateBackend.bundle';target.mkdir(parents=True,exist_ok=True)
  (target/'RateBackend').write_bytes(patched)
  info={'CFBundleIdentifier':'com.ning.cellularrate.backend','CFBundleExecutable':'RateBackend','CFBundleName':'NingCellularRateBackend','CFBundlePackageType':'BNDL','CFBundleVersion':'1','NSPrincipalClass':'NNCellularRateModule','MinimumOSVersion':'16.0'}
  (target/'Info.plist').write_bytes(plistlib.dumps(info));report.append(r)
 (ROOT/'build/backend-relocation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
