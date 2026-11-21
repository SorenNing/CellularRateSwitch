"""Permit helper signature renewal, but never alter its logic or entitlements."""
import struct,plistlib,hashlib
from binary_checks import require

def helper_slices(data):
 require(data[:4]==b'\xca\xfe\xba\xbe','original helper must stay universal')
 out={}
 for i in range(struct.unpack_from('>I',data,4)[0]):
  cpu,sub,off,size,align=struct.unpack_from('>5I',data,8+i*20);b=data[off:off+size];p=32;sections={};entitlements=None;deps=[]
  require(struct.unpack_from('<II',b,4)==(cpu,sub),'fat/thin mismatch')
  for _ in range(struct.unpack_from('<I',b,16)[0]):
   cmd,length=struct.unpack_from('<II',b,p)
   if cmd==0x19:
    for j in range(struct.unpack_from('<I',b,p+64)[0]):
     q=p+72+j*80;sect=b[q:q+16].split(b'\0')[0].decode();seg=b[q+16:q+32].split(b'\0')[0].decode();addr,ln,fo=struct.unpack_from('<QQI',b,q+32);flags=struct.unpack_from('<I',b,q+64)[0]
     if (flags&255) not in (1,12,18) and fo and ln:sections[(seg,sect)]=hashlib.sha256(b[fo:fo+ln]).hexdigest()
   elif cmd==0x1d:
    sigoff,siglen=struct.unpack_from('<II',b,p+8);sig=b[sigoff:sigoff+siglen];magic,total,count=struct.unpack_from('>3I',sig);require(magic==0xfade0cc0,'signature header')
    for j in range(count):
     slot,at=struct.unpack_from('>II',sig,12+j*8)
     if slot==5:
      magic,sz=struct.unpack_from('>II',sig,at);require(magic==0xfade7171,'XML entitlement slot');entitlements=plistlib.loads(sig[at+8:at+sz])
   elif cmd in (0xc,0x80000018,0x8000001f,0x20,0x80000023):
    at=struct.unpack_from('<I',b,p+8)[0];deps.append(b[p+at:p+length].split(b'\0')[0].decode())
   p+=length
  require(entitlements is not None and sections,'helper metadata missing');out[sub]={'cpu':cpu,'sections':sections,'entitlements':entitlements,'dependencies':deps}
 return out

def compare_helper(original,renewed):
 old=helper_slices(original);new=helper_slices(renewed);require(set(old)==set(new)=={0,0x80000002},'helper architecture changed')
 for sub in old:
  require(old[sub]==new[sub],'helper code, constants, entitlements, or dependencies changed')
 return {'all_file_backed_sections_unchanged':True,'original_entitlements_preserved':True,'architectures':['arm64','arm64e'],'signature_may_change':True}
