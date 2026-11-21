#import "NINGCRBackend.h"
#import <UIKit/UIKit.h>
#import <objc/runtime.h>
#import <objc/message.h>
#import <stdlib.h>
#import <string.h>

@interface NINGCRBackendLocation : NSObject @end
@implementation NINGCRBackendLocation @end
static NSError *NINGCRBackendError(NSString *message) {
    return [NSError errorWithDomain:@"com.ning.cellularrate.backend" code:1 userInfo:@{NSLocalizedDescriptionKey:message}];
}
id NINGCRCreateBackend(NSError **error) {
    if (!NSThread.isMainThread) { if(error)*error=NINGCRBackendError(@"请在主线程展开蜂窝模块");return nil; }
    NSBundle *owner=[NSBundle bundleForClass:NINGCRBackendLocation.class];
    NSString *path=[owner.bundlePath stringByAppendingPathComponent:@"RateBackend.bundle"];
    NSBundle *bundle=[NSBundle bundleWithPath:path];
    NSError *loadError=nil;
    if (!bundle || ![bundle loadAndReturnError:&loadError]) {
        if(error)*error=loadError?:NINGCRBackendError(@"蜂窝后端载入失败，请确认安装包完整");return nil;
    }
    Class cls=NSClassFromString(@"NNCellularRateModuleViewController");
    if (!cls || ![cls isSubclassOfClass:UIViewController.class]) { if(error)*error=NINGCRBackendError(@"蜂窝后端类型不匹配");return nil; }
    Method method=class_getInstanceMethod(cls,NSSelectorFromString(@"updatedMenuItems"));
    char *result=method?method_copyReturnType(method):NULL;
    BOOL valid=method && method_getNumberOfArguments(method)==2 && result && result[0]=='@';free(result);
    if(!valid) { if(error)*error=NINGCRBackendError(@"蜂窝后端接口不匹配");return nil; }
    @try {
        UIViewController *controller=[[cls alloc] initWithNibName:nil bundle:bundle];
        if(!controller) { if(error)*error=NINGCRBackendError(@"蜂窝后端初始化失败");return nil; }
        return controller;
    } @catch(NSException *exception) {
        if(error)*error=NINGCRBackendError(@"蜂窝后端暂不可用，请关闭后重试");return nil;
    }
}
