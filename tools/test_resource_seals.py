"""Synthetic unit fixtures only, not a substitute for Apple codesign validation."""
import struct,hashlib,plistlib,copy
from resource_seals import verify_bundle_seal

def fixture():
 base='Example.bundle/';info=plistlib.dumps({'CFBundleExecutable':'Example'});asset=b'resource-data'
 resources=plistlib.dumps({'files2':{'icon.png':{'hash2':hashlib.sha256(asset).digest()}}})
 cd=bytearray(224);struct.pack_into('>9I',cd,0,0xfade0c02,len(cd),0x20200,2,192,44,3,0,0);struct.pack_into('4B',cd,36,32,2,0,12)
 cd[160:192]=hashlib.sha256(info).digest();cd[96:128]=hashlib.sha256(resources).digest()
 sig=struct.pack('>5I',0xfade0cc0,20+len(cd),1,0,20)+cd
 header=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,16,0,0);binary=header+struct.pack('<4I',0x1d,16,48,len(sig))+sig
 files={base+'Info.plist':(info,0o644),base+'_CodeSignature/CodeResources':(resources,0o644),base+'icon.png':(asset,0o644),base+'Example':(binary,0o755)}
 return base,files

def main():
 base,files=fixture();assert verify_bundle_seal(files,base,'Example')['hashed_resources_verified']==1
 for key in ('Info.plist','_CodeSignature/CodeResources','icon.png'):
  bad=copy.deepcopy(files);data,mode=bad[base+key];bad[base+key]=(data+b'changed',mode)
  try:verify_bundle_seal(bad,base,'Example')
  except ValueError:pass
  else:raise AssertionError('tampered resource accepted: '+key)
 bad=copy.deepcopy(files);del bad[base+'_CodeSignature/CodeResources']
 try:verify_bundle_seal(bad,base,'Example')
 except KeyError:pass
 else:raise AssertionError('missing outer seal accepted')
 print('RESOURCE_SEAL_UNIT_OK: valid fixture, three tampering negatives, missing seal negative; not native signing')
if __name__=='__main__':main()
