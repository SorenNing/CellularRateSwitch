"""Validate external bundle Info/CodeResources hashes bound into CodeDirectory."""
import struct,hashlib,plistlib,posixpath
from binary_checks import require

def verify_bundle_seal(files,base,executable):
 info=files[base+'Info.plist'][0];resources=files[base+'_CodeSignature/CodeResources'][0]
 binary=files[base+executable][0];require(binary[:4]==b'\xcf\xfa\xed\xfe','bundle executable must be thin')
 q=32;sig=None
 for _ in range(struct.unpack_from('<I',binary,16)[0]):
  cmd,sz=struct.unpack_from('<II',binary,q)
  if cmd==0x1d:
   off,ln=struct.unpack_from('<II',binary,q+8);sig=binary[off:off+ln]
  q+=sz
 require(sig is not None,'bundle signature missing');count=struct.unpack_from('>I',sig,8)[0];cd=None
 for i in range(count):
  slot,off=struct.unpack_from('>II',sig,12+i*8)
  if slot==0:
   ln=struct.unpack_from('>I',sig,off+4)[0];cd=sig[off:off+ln]
 require(cd is not None,'CodeDirectory missing');hashoff=struct.unpack_from('>I',cd,16)[0];special=struct.unpack_from('>I',cd,24)[0];size,kind=struct.unpack_from('BB',cd,36)
 algorithm={1:'sha1',2:'sha256',3:'sha256',4:'sha384'}[kind];require(special>=3,'bundle has no external resource slots')
 for slot,content in [(1,info),(3,resources)]:
  digest=hashlib.new(algorithm,content).digest()[:size];require(digest==cd[hashoff-slot*size:hashoff-(slot-1)*size],'bundle external special-slot mismatch')
 seal=plistlib.loads(resources);checked=set()
 for group in ('files','files2'):
  for name,record in seal.get(group,{}).items():
   require(not name.startswith('/') and '..' not in name.split('/'),'unsafe resource seal path')
   path=base+name
   if isinstance(record,bytes):hashes=[('sha1',record)]
   elif isinstance(record,dict):hashes=[(algorithm,record[key]) for key,algorithm in [('hash','sha1'),('hash2','sha256')] if key in record]
   else:raise ValueError('resource record type')
   for algorithm,digest in hashes:
    require(path in files,'sealed resource missing: '+name);require(hashlib.new(algorithm,files[path][0]).digest()==digest,'sealed resource mismatch: '+name);checked.add(name)
 return {'Info_plist_bound_to_signature':True,'CodeResources_bound_to_signature':True,'hashed_resources_verified':len(checked),'nested_code_requires_macos_validation':True}
