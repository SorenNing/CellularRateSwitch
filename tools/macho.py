"""Mach-O parser and signature validation; never executes payloads."""
import struct
from binary_checks import require,signature,chained_formats,sha256

def inspect(data,expected=None):
 if data[:4]==b'\xca\xfe\xba\xbe':
  n=struct.unpack_from('>I',data,4)[0];require(0<n<=4,'fat count')
  slices=[struct.unpack_from('>IIIII',data,8+20*i) for i in range(n)]
 else:
  require(data[:4]==b'\xcf\xfa\xed\xfe','Mach-O magic');cpu,sub=struct.unpack_from('<II',data,4);slices=[(cpu,sub,0,len(data),0)]
 report=[]
 for cpu,sub,off,size,align in slices:
  b=data[off:off+size];require(len(b)==size and size>=32,'slice bounds')
  _,tcpu,tsub,kind,n,cmdsz,_,_=struct.unpack_from('<8I',b);require((cpu,sub)==(tcpu,tsub),'fat/thin mismatch');require(cpu==0x100000c,'CPU')
  require(sub in (0,0x80000002),'real arm64/arm64e required')
  pos=32;commands={};loads=[];names=[]
  for _ in range(n):
   cmd,sz=struct.unpack_from('<II',b,pos);require(sz>=8 and pos+sz<=32+cmdsz,'load command bounds')
   if cmd in (0xc,0x80000018,0x8000001f,0x20,0x80000023,0xd):
    at=struct.unpack_from('<I',b,pos+8)[0];name=b[pos+at:pos+sz].split(b'\0')[0].decode();(names if cmd==0xd else loads).append(name)
   if cmd in (0x1d,0x80000034):commands[cmd]=struct.unpack_from('<II',b,pos+8)
   pos+=sz
  require(pos==32+cmdsz,'load command size');require(0x1d in commands,'unsigned binary')
  signed=signature(b,*commands[0x1d]);fixups=chained_formats(b,*commands[0x80000034],sub) if 0x80000034 in commands else None
  require(not any(any(x in p.lower() for x in ('substrate','c18five','controlcenter18','ellekit')) for p in loads),'foreign tweak dependency')
  report.append({'cpu':hex(cpu),'subtype':hex(sub),'filetype':kind,'size':size,'loads':loads,'install_names':names,'signature':signed,'fixups':fixups})
 if expected is not None:require({r['subtype'] for r in report}=={hex(expected)},'wrong architecture')
 return {'sha256':sha256(data),'size':len(data),'slices':report}
