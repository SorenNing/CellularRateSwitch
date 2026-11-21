// The original backend's sole posix_spawn import is bound to this private symbol.
// Preserve its argv (including argv[0]), attributes and environment unchanged.
// Only redirect the executable path to the original signed helper next to us.
#include <spawn.h>
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <unistd.h>

__attribute__((visibility("default")))
int ning__spawn(pid_t *pid, const char *path,
 const posix_spawn_file_actions_t *actions, const posix_spawnattr_t *attributes,
 char *const argv[], char *const envp[]) {
    (void)path;
    Dl_info info;
    if (!dladdr((const void *)&ning__spawn, &info) || !info.dli_fname) return ENOENT;
    char helper[PATH_MAX];
    size_t length=strlen(info.dli_fname);
    if (length>=sizeof(helper)) return ENAMETOOLONG;
    memcpy(helper,info.dli_fname,length+1);
    char *slash=strrchr(helper,'/');
    if (!slash) return ENOENT;
    const char *name="NingCellularRateTool";
    size_t prefix=(size_t)(slash-helper)+1;
    if (prefix+strlen(name)+1>sizeof(helper)) return ENAMETOOLONG;
    memcpy(helper+prefix,name,strlen(name)+1);
    if (access(helper,X_OK)!=0) return errno;
    typedef int (*Spawn)(pid_t *,const char *,const posix_spawn_file_actions_t *,const posix_spawnattr_t *,char *const[],char *const[]);
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_NOW|RTLD_LOCAL);
    if (!system) return ENOSYS;
    Spawn spawn=(Spawn)dlsym(system,"posix_spawn");
    int result=spawn?spawn(pid,helper,actions,attributes,argv,envp):ENOSYS;
    dlclose(system);
    return result;
}
