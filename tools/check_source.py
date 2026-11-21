"""Checks extracted production readback policy, not an iOS runtime test."""
from pathlib import Path
import re,subprocess,tempfile,json,hashlib,plistlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 source=(ROOT/'src/NINGCRModule.m').read_text()
 for denied in ('C18FiveLiveShell','C18ModuleView','MSHookMessageEx','__attribute__((constructor))'):
  assert denied not in source,denied
 assert 'method_copyReturnType' in source and 'method_copyArgumentType' in source
 a=source.index('typedef struct {');b=source.index('@interface NINGCRRow',a);policy=source[a:b]
 harness='''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
POLICY
int main(void) {
 unsigned checks=0;
 for (int target=0;target<=5;target++) {
  NINGCRReadbackState s={0};
  assert(!NINGCRReadbackBegin(&s,target,1));checks++;
  NINGCRReadbackActivate(&s);
  uint64_t t=NINGCRReadbackBegin(&s,target,1);
  if(target!=0&&target!=4&&target!=5){assert(!t);checks++;continue;}
  assert(t && s.busy && s.deadline==9);checks++;
  assert(!NINGCRReadbackBegin(&s,target,2));checks++;
  for(int selected=0;selected<=5;selected++) {
   if(selected!=0&&selected!=4&&selected!=5)continue;
   for(int i=0;i<=1000;i++) {
    NINGCRReadbackState q=s;double now=1.+i*.01;
    int r=NINGCRReadbackObserve(&q,t,selected,now);
    if(selected&&(!target||selected==target)&&now<=9)assert(r==NINGCRReadbackConfirmed&&!q.busy);
    else if(now>=9)assert(r==NINGCRReadbackUnconfirmed&&!q.busy);
    else assert(r==NINGCRReadbackWaiting&&q.busy);
    checks++;
   }
  }
  NINGCRReadbackInvalidate(&s);assert(!NINGCRReadbackAccepts(&s,t));checks++;
  assert(NINGCRReadbackObserve(&s,t,5,2)==NINGCRReadbackStale);checks++;
  NINGCRReadbackActivate(&s);assert(!NINGCRReadbackAccepts(&s,t));checks++;
 }
 for(int a=0;a<2;a++)for(int b=0;b<2;b++){
  assert(NINGCRExclusiveGeneration(2,5,a,4,b)==(a==b?0:a?5:4));checks++;
  assert(NINGCRExclusiveGeneration(2,4,a,5,b)==(a==b?0:a?4:5));checks++;
 }
 assert(!NINGCRExclusiveGeneration(2,5,1,5,0));checks++;
 printf("READBACK_CHECKS %u\\n",checks);return 0;
}
'''.replace('POLICY',policy)
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'test.c';p.write_text(harness);exe=Path(d)/'test'
  subprocess.run(['clang','-std=c11','-Wall','-Wextra',str(p),'-o',str(exe)],check=True,capture_output=True)
  result=subprocess.run([str(exe)],check=True,capture_output=True,text=True).stdout.strip()
 info=plistlib.loads((ROOT/'Resources/Info.plist').read_bytes());assert info['NSPrincipalClass']=='NINGCRModule';assert info['CFBundleIdentifier']=='com.ning.cellularrate.module'
 print(json.dumps({'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'policy_result':result,'iOS_runtime_tested':False},indent=2))
if __name__=='__main__':main()
