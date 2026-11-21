#import <UIKit/UIKit.h>
#import <Foundation/Foundation.h>
#import <QuartzCore/QuartzCore.h>
#import <objc/message.h>
#import <objc/runtime.h>
#import <stdint.h>
#import <stdlib.h>
#import <string.h>
#import "NINGCRBackend.h"

@class CCUIContentModuleContext;
@protocol CCUIContentModuleContentViewController <NSObject>
- (double)preferredExpandedContentHeight;
@optional
- (double)preferredExpandedContentWidth;
- (bool)providesOwnPlatter;
- (bool)shouldBeginTransitionToExpandedContentModule;
- (bool)shouldFinishTransitionToExpandedContentModule;
- (void)willTransitionToExpandedContentMode:(bool)expanded;
- (void)didTransitionToExpandedContentMode:(bool)expanded;
- (void)controlCenterWillPresent;
- (void)controlCenterDidDismiss;
@end
@protocol CCUIContentModule <NSObject>
- (UIViewController<CCUIContentModuleContentViewController> *)contentViewController;
@optional
- (UIViewController *)backgroundViewController;
- (void)setContentModuleContext:(CCUIContentModuleContext *)context;
@end
@interface CCUIContentModuleContext : NSObject
- (void)requestExpandModule;
@end

@interface NINGCRChoice : NSObject
@property(nonatomic) NSInteger generation;
@property(nonatomic,strong) id nativeItem;
@property(nonatomic) BOOL selected;
@end
@implementation NINGCRChoice @end

static BOOL NINGCRType(const char *actual,const char *expected) {
    if(!actual||!expected)return NO;
    while(*actual&&strchr("rnNoORV",*actual))actual++;
    if(!strcmp(expected,"@"))return actual[0]=='@'&&actual[1]!='?';
    if(!strcmp(expected,"B"))return actual[0]=='B'||actual[0]=='c';
    if(expected[0]=='@')return actual[0]=='@'&&actual[1]!='?';
    if(expected[0]==':'||(expected[0]&&!expected[1]))return actual[0]==expected[0];
    return !strcmp(actual,expected);
}
static BOOL NINGCRMatch(Method method,const char *result,NSArray<NSString *> *arguments) {
    if(!method||method_getNumberOfArguments(method)!=arguments.count+2)return NO;
    char *type=method_copyReturnType(method);BOOL valid=NINGCRType(type,result);free(type);
    for(NSUInteger i=0;valid&&i<arguments.count+2;i++){
        const char *expected=i==0?"@":i==1?":":arguments[i-2].UTF8String;
        type=method_copyArgumentType(method,(unsigned int)i);valid=NINGCRType(type,expected);free(type);
    }
    return valid;
}
static Method NINGCRMethod(id object,SEL selector) {
    return object?class_getInstanceMethod(object_getClass(object),selector):NULL;
}
static id NINGCRObject(id object,NSString *name) {
    SEL selector=NSSelectorFromString(name);
    if(!NINGCRMatch(NINGCRMethod(object,selector),"@",@[]))return nil;
    @try{return ((id(*)(id,SEL))objc_msgSend)(object,selector);}
    @catch(__unused NSException *e){return nil;}
}
static NSInteger NINGCRGeneration(id item) {
    id value=NINGCRObject(item,@"identifier");if(![value isKindOfClass:NSString.class])return 0;
    NSString *key=[value stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet].uppercaseString;
    if([key isEqualToString:@"5G"])return 5;if([key isEqualToString:@"4G"])return 4;return 0;
}
static BOOL NINGCRCanInvoke(id item) {
    return NINGCRMatch(NINGCRMethod(item,NSSelectorFromString(@"performAction")),"B",@[]);
}
static BOOL NINGCRInvokeAction(id item) {
    SEL selector=NSSelectorFromString(@"performAction");Method method=NINGCRMethod(item,selector);
    if(!NINGCRMatch(method,"B",@[]))return NO;
    char *type=method_copyReturnType(method);if(!type)return NO;
    const char *actual=type;while(*actual&&strchr("rnNoORV",*actual))actual++;
    BOOL nativeBool=actual[0]=='B';free(type);
    if(nativeBool)return ((_Bool(*)(id,SEL))objc_msgSend)(item,selector);
    return ((signed char(*)(id,SEL))objc_msgSend)(item,selector)!=0;
}
static BOOL NINGCRReadSelected(id item,BOOL *value) {
    SEL selector=NSSelectorFromString(@"isSelected");Method method=NINGCRMethod(item,selector);
    @try{
        if(NINGCRMatch(method,"@",@[])){
            id selected=((id(*)(id,SEL))objc_msgSend)(item,selector);
            if(![selected isKindOfClass:NSNumber.class])return NO;
            *value=[selected boolValue];return YES;
        }
        if(!NINGCRMatch(method,"B",@[]))return NO;
        char *encoding=method_copyReturnType(method);if(!encoding)return NO;
        const char *actual=encoding;while(*actual&&strchr("rnNoORV",*actual))actual++;
        BOOL nativeBool=actual[0]=='B';free(encoding);
        *value=nativeBool?((_Bool(*)(id,SEL))objc_msgSend)(item,selector):((signed char(*)(id,SEL))objc_msgSend)(item,selector)!=0;return YES;
    }@catch(__unused NSException *e){return NO;}
}
static id NINGCRIvar(id object,const char *name) {
    if(!object)return nil;Ivar ivar=class_getInstanceVariable(object_getClass(object),name);
    return ivar&&NINGCRType(ivar_getTypeEncoding(ivar),"@")?object_getIvar(object,ivar):nil;
}
static NSArray<NINGCRChoice *> *NINGCRReadChoices(id backend) {
    SEL selector=NSSelectorFromString(@"updatedMenuItems");
    id raw=NINGCRMatch(NINGCRMethod(backend,selector),"@",@[])?NINGCRObject(backend,@"updatedMenuItems"):NINGCRIvar(backend,"_menuItems");
    if(![raw isKindOfClass:NSArray.class])return @[];
    NSMutableDictionary<NSNumber *,NINGCRChoice *> *found=[NSMutableDictionary dictionary];
    for(id item in raw){
        NSInteger generation=NINGCRGeneration(item);BOOL selected=NO;if(!generation)continue;
        if(found[@(generation)]||!NINGCRCanInvoke(item)||!NINGCRReadSelected(item,&selected))return @[];
        NINGCRChoice *choice=[NINGCRChoice new];choice.generation=generation;choice.nativeItem=item;
        choice.selected=selected;found[@(generation)]=choice;
    }
    if(found.count!=2)return @[];return @[found[@5],found[@4]];
}
static int NINGCRExclusiveGeneration(unsigned count,long first,int firstSelected,long second,int secondSelected);
static NSInteger NINGCRSelectedGeneration(NSArray<NINGCRChoice *> *choices) {
    if(choices.count!=2)return 0;
    return NINGCRExclusiveGeneration((unsigned)choices.count,choices[0].generation,choices[0].selected,
                                    choices[1].generation,choices[1].selected);
}

typedef struct { uint64_t generation; int active,busy,target; double deadline; } NINGCRReadbackState;
typedef enum { NINGCRReadbackStale, NINGCRReadbackWaiting, NINGCRReadbackConfirmed, NINGCRReadbackUnconfirmed } NINGCRReadbackResult;
static const double NINGCRReadbackInterval=.20,NINGCRReadbackTimeout=8.0;
static void NINGCRReadbackInvalidate(NINGCRReadbackState *state){state->generation++;state->active=0;state->busy=0;state->target=0;state->deadline=0;}
static void NINGCRReadbackActivate(NINGCRReadbackState *state){NINGCRReadbackInvalidate(state);state->active=1;}
static uint64_t NINGCRReadbackBegin(NINGCRReadbackState *state,int target,double now){if(!state->active||state->busy||(target!=0&&target!=4&&target!=5))return 0;state->generation++;state->busy=1;state->target=target;state->deadline=now+NINGCRReadbackTimeout;return state->generation;}
static int NINGCRReadbackAccepts(const NINGCRReadbackState *state,uint64_t token){return token&&state->active&&state->busy&&state->generation==token;}
static int NINGCRExclusiveGeneration(unsigned count,long first,int firstSelected,long second,int secondSelected){if(count!=2||!((first==5&&second==4)||(first==4&&second==5))||!!firstSelected==!!secondSelected)return 0;return (int)(firstSelected?first:second);}
static NINGCRReadbackResult NINGCRReadbackObserve(NINGCRReadbackState *state,uint64_t token,int selectedGeneration,double now){if(!NINGCRReadbackAccepts(state,token))return NINGCRReadbackStale;if(selectedGeneration&&(!state->target||selectedGeneration==state->target)&&now<=state->deadline){state->busy=0;return NINGCRReadbackConfirmed;}if(now>=state->deadline){state->busy=0;return NINGCRReadbackUnconfirmed;}return NINGCRReadbackWaiting;}

@interface NINGCRRow : UIControl
@property(nonatomic,strong) UILabel *capsule;
@property(nonatomic,strong) UILabel *label;
@property(nonatomic) NSInteger generation;
- (void)updateWithChoice:(NINGCRChoice *)choice;
@end
@implementation NINGCRRow
- (instancetype)initWithFrame:(CGRect)frame {if(!(self=[super initWithFrame:frame]))return nil;self.backgroundColor=UIColor.clearColor;self.isAccessibilityElement=YES;_capsule=[UILabel new];_capsule.textAlignment=NSTextAlignmentCenter;_capsule.font=[UIFont systemFontOfSize:13 weight:UIFontWeightSemibold];_capsule.textColor=UIColor.whiteColor;_capsule.layer.cornerRadius=11.5;_capsule.layer.cornerCurve=kCACornerCurveContinuous;_capsule.clipsToBounds=YES;_capsule.userInteractionEnabled=NO;[self addSubview:_capsule];_label=[UILabel new];_label.font=[UIFont systemFontOfSize:16 weight:UIFontWeightRegular];_label.textColor=UIColor.whiteColor;_label.userInteractionEnabled=NO;_label.adjustsFontSizeToFitWidth=YES;_label.minimumScaleFactor=.75;[self addSubview:_label];return self;}
- (void)updateWithChoice:(NINGCRChoice *)choice {self.generation=choice.generation;self.label.text=choice.generation==5?@"切换5G":@"切换4G";self.capsule.text=choice.selected?@"✓":@"";self.capsule.backgroundColor=choice.selected?[UIColor colorWithRed:.20 green:.78 blue:.35 alpha:1]:[UIColor colorWithWhite:1 alpha:.16];self.accessibilityLabel=self.label.text;self.accessibilityValue=choice.selected?@"已选中":@"未选中";self.accessibilityTraits=UIAccessibilityTraitButton|(choice.selected?UIAccessibilityTraitSelected:0);[self setNeedsLayout];}
- (void)layoutSubviews { [super layoutSubviews];CGFloat w=self.bounds.size.width,h=self.bounds.size.height,bw=36,gap=12;CGFloat cw=MIN(ceil([self.label sizeThatFits:CGSizeMake(CGFLOAT_MAX,h)].width),MAX(0,w-32-bw-gap));CGFloat x=(w-bw-gap-cw)*.5;self.capsule.frame=CGRectMake(x,(h-23)*.5,bw,23);self.label.frame=CGRectMake(x+bw+gap,0,cw,h); }
- (void)setHighlighted:(BOOL)value {[super setHighlighted:value];self.backgroundColor=value?[UIColor colorWithWhite:1 alpha:.08]:UIColor.clearColor;}
@end

@interface NINGCRController : UIViewController <CCUIContentModuleContentViewController>
@property(nonatomic,strong) id backend;
@property(nonatomic,strong) CCUIContentModuleContext *moduleContext;
- (BOOL)isCurrentSession;
- (void)refresh;
- (void)startReadbackForGeneration:(NSInteger)generation item:(id)item;
- (void)scheduleReadback:(uint64_t)token;
- (void)pollReadback:(uint64_t)token session:(NSUInteger)session;
@end
@implementation NINGCRController {
    NINGCRReadbackState _readback;
    BOOL _expanded,_sessionActive,_controlCenterPresented;
    NSUInteger _session;
    UIVisualEffectView *_material;
    UIButton *_compactButton;
    UIImageView *_glyph;
    UILabel *_heading,*_message;
    UIView *_divider,*_list;
    NSArray<NINGCRRow *> *_rows;
    NSArray<NINGCRChoice *> *_choices;
}
- (double)preferredExpandedContentHeight{return 228;}
- (double)preferredExpandedContentWidth{return 336;}
- (void)loadView {
    self.preferredContentSize=CGSizeMake(336,228);UIView *v=[[UIView alloc]initWithFrame:CGRectMake(0,0,336,228)];v.backgroundColor=UIColor.clearColor;v.layer.cornerRadius=44;v.layer.cornerCurve=kCACornerCurveContinuous;v.clipsToBounds=YES;self.view=v;
    _material=[[UIVisualEffectView alloc]initWithEffect:[UIBlurEffect effectWithStyle:UIBlurEffectStyleSystemChromeMaterialDark]];_material.frame=v.bounds;_material.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;[v addSubview:_material];
    _compactButton=[UIButton buttonWithType:UIButtonTypeSystem];_compactButton.tintColor=UIColor.whiteColor;UIImage *antenna=[UIImage systemImageNamed:@"antenna.radiowaves.left.and.right"];[_compactButton setImage:antenna forState:UIControlStateNormal];_compactButton.imageView.contentMode=UIViewContentModeScaleAspectFit;[_compactButton addTarget:self action:@selector(requestExpand) forControlEvents:UIControlEventTouchUpInside];_compactButton.frame=CGRectMake(0,0,64,64);[v addSubview:_compactButton];
    UILongPressGestureRecognizer *longPress=[[UILongPressGestureRecognizer alloc]initWithTarget:self action:@selector(longPress:)];[_compactButton addGestureRecognizer:longPress];
    _glyph=[[UIImageView alloc]initWithImage:antenna];_glyph.tintColor=UIColor.whiteColor;_glyph.contentMode=UIViewContentModeScaleAspectFit;[v addSubview:_glyph];
    _heading=[UILabel new];_heading.text=@"蜂窝4/5G切换";_heading.textColor=UIColor.whiteColor;_heading.font=[UIFont systemFontOfSize:18 weight:UIFontWeightSemibold];_heading.textAlignment=NSTextAlignmentCenter;[v addSubview:_heading];
    _divider=[UIView new];_divider.backgroundColor=[UIColor colorWithWhite:1 alpha:.25];[v addSubview:_divider];_list=[UIView new];[v addSubview:_list];
    NSMutableArray *rows=[NSMutableArray array];for(int i=0;i<2;i++){NINGCRRow *row=[[NINGCRRow alloc]initWithFrame:CGRectZero];[row addTarget:self action:@selector(choose:) forControlEvents:UIControlEventTouchUpInside];[_list addSubview:row];[rows addObject:row];}_rows=rows;
    _message=[UILabel new];_message.font=[UIFont systemFontOfSize:14];_message.numberOfLines=3;_message.textColor=UIColor.whiteColor;_message.textAlignment=NSTextAlignmentCenter;_message.text=@"无法读取4G/5G选项，请关闭后重试";_message.userInteractionEnabled=YES;[_message addGestureRecognizer:[[UITapGestureRecognizer alloc]initWithTarget:self action:@selector(retryMessage:)]];[_list addSubview:_message];[self updatePresentation];
}
- (bool)providesOwnPlatter { return false; }
- (bool)shouldBeginTransitionToExpandedContentModule { return true; }
- (bool)shouldFinishTransitionToExpandedContentModule { return true; }
- (BOOL)isCurrentSession { return NSThread.isMainThread && _expanded && _sessionActive && self.viewIfLoaded.window!=nil; }
- (void)beginExpandedSession {
    if (!_expanded || _sessionActive || !self.viewIfLoaded.window) return;
    _sessionActive=YES; _session++; NINGCRReadbackActivate(&_readback);
    [self updatePresentation]; [self refresh];
}
- (void)endExpandedSessionAndCollapse:(BOOL)collapse {
    BOOL changed=_expanded||_sessionActive;
    if (collapse) _expanded=NO;
    if (changed) { _sessionActive=NO; _session++; NINGCRReadbackInvalidate(&_readback); }
    if (collapse) [self updatePresentation];
}
- (void)requestExpand { if ([self.moduleContext respondsToSelector:@selector(requestExpandModule)]) [self.moduleContext requestExpandModule]; }
- (void)longPress:(UILongPressGestureRecognizer *)gesture {if(gesture.state==UIGestureRecognizerStateBegan)[self requestExpand];}
- (void)willTransitionToExpandedContentMode:(bool)expanded {if(!expanded)[self endExpandedSessionAndCollapse:YES];}
- (void)didTransitionToExpandedContentMode:(bool)expanded {
    if (expanded) { if (!_expanded) { _expanded=YES; [self updatePresentation]; } [self beginExpandedSession]; }
    else [self endExpandedSessionAndCollapse:YES];
}
- (void)controlCenterWillPresent { _controlCenterPresented=YES; }
- (void)controlCenterDidDismiss { _controlCenterPresented=NO; [self endExpandedSessionAndCollapse:YES]; }
- (void)viewDidAppear:(BOOL)animated { [super viewDidAppear:animated]; if (_expanded && !_sessionActive) [self beginExpandedSession]; }
- (void)viewWillDisappear:(BOOL)animated {
    [super viewWillDisappear:animated];
    if (_sessionActive) { _sessionActive=NO; _session++; NINGCRReadbackInvalidate(&_readback); }
}
- (void)viewDidLayoutSubviews {[super viewDidLayoutSubviews];CGFloat w=self.view.bounds.size.width,h=self.view.bounds.size.height,scale=self.view.window.screen.scale?:UIScreen.mainScreen.scale;_compactButton.frame=CGRectMake((w-64)*.5,(h-64)*.5,64,64);_glyph.frame=CGRectMake((w-32)*.5,20,32,32);_heading.frame=CGRectMake(16,62,w-32,27);_divider.frame=CGRectMake(0,102,w,1/MAX(1,scale));_list.frame=CGRectMake(0,104,w,MAX(0,h-104));CGFloat rh=MAX(56,MIN(66,MAX(0,h-104)/2));for(NSUInteger i=0;i<_rows.count;i++)_rows[i].frame=CGRectMake(0,i*rh,w,rh);_message.frame=_list.bounds;if(_expanded&&!_sessionActive&&self.view.window)[self beginExpandedSession];}
- (void)updatePresentation {
    BOOL expanded=_expanded;_compactButton.hidden=expanded;_glyph.hidden=!expanded;_heading.hidden=!expanded;_divider.hidden=!expanded;_list.hidden=!expanded;
    self.preferredContentSize=expanded?CGSizeMake(336,228):CGSizeMake(64,64);
    if(!expanded){_material.hidden=YES;self.view.layer.cornerRadius=16;}else{_material.hidden=NO;self.view.layer.cornerRadius=44;}
    [self.view setNeedsLayout];
}
- (void)renderChoices:(NSArray<NINGCRChoice *> *)choices {if(![self isCurrentSession]||!NINGCRSelectedGeneration(choices))return;_choices=choices;for(NSUInteger i=0;i<2;i++){[_rows[i] updateWithChoice:choices[i]];_rows[i].hidden=NO;}_message.hidden=YES;if(!_readback.busy)for(NINGCRRow *row in _rows)row.userInteractionEnabled=YES;}
- (void)endReadback {if(!NSThread.isMainThread)return;NINGCRReadbackInvalidate(&_readback);for(NINGCRRow *row in _rows)row.userInteractionEnabled=NO;}
- (void)refresh {
    if(![self isCurrentSession]||_readback.busy)return;
    if(!self.backend){NSError *error=nil;id backend=NINGCRCreateBackend(&error);if(![self isCurrentSession])return;if(!backend){_message.text=error.localizedDescription?:@"无法连接蜂窝控制器，点按重试";_message.hidden=NO;return;}self.backend=backend;}
    NSArray *choices=NINGCRReadChoices(self.backend);if(![self isCurrentSession])return;
    if(NINGCRSelectedGeneration(choices)){[self renderChoices:choices];_heading.text=@"蜂窝4/5G切换";}
    else{_message.text=@"无法读取4G/5G选项，点按重试";_message.hidden=NO;[self startReadbackForGeneration:0 item:nil];}
}
- (void)startReadbackForGeneration:(NSInteger)generation item:(id)item {
    if(![self isCurrentSession]||_readback.busy)return;if(!_readback.active)NINGCRReadbackActivate(&_readback);
    uint64_t token=NINGCRReadbackBegin(&_readback,(int)generation,CACurrentMediaTime());if(!token)return;
    for(NINGCRRow *row in _rows)row.userInteractionEnabled=NO;
    _heading.text=generation==5?@"正在确认5G…":generation==4?@"正在确认4G…":@"正在读取4G/5G…";
    if(item){@try{(void)NINGCRInvokeAction(item);}@catch(__unused NSException *e){}}
    [self scheduleReadback:token];
}
- (void)scheduleReadback:(uint64_t)token {if(!NINGCRReadbackAccepts(&_readback,token))return;if(![self isCurrentSession]){[self endReadback];return;}double delay=MIN(NINGCRReadbackInterval,MAX(0,_readback.deadline-CACurrentMediaTime()));NSUInteger session=_session;__weak NINGCRController *weakSelf=self;dispatch_after(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(delay*NSEC_PER_SEC)),dispatch_get_main_queue(),^{NINGCRController *strong=weakSelf;if(!strong||session!=strong->_session)return;[strong pollReadback:token session:session];});}
- (void)pollReadback:(uint64_t)token session:(NSUInteger)session {
    if(!NSThread.isMainThread||session!=_session||!NINGCRReadbackAccepts(&_readback,token))return;
    if(![self isCurrentSession]){[self endReadback];return;}
    NSArray *choices=NINGCRReadChoices(self.backend);
    if(!NINGCRReadbackAccepts(&_readback,token)||session!=_session)return;
    if(![self isCurrentSession]){[self endReadback];return;}
    NSInteger selected=NINGCRSelectedGeneration(choices);
    NINGCRReadbackResult result=NINGCRReadbackObserve(&_readback,token,(int)selected,CACurrentMediaTime());
    if(result==NINGCRReadbackStale)return;
    if(selected)[self renderChoices:choices];
    if(result==NINGCRReadbackWaiting){[self scheduleReadback:token];return;}
    _heading.text=result==NINGCRReadbackConfirmed?@"蜂窝4/5G切换":(_readback.target?@"切换状态未确认，请稍后重试":@"暂未读到4G/5G状态");
    if(!selected){_choices=nil;for(NINGCRRow *row in _rows){row.hidden=YES;row.accessibilityValue=@"状态未知";row.accessibilityTraits=UIAccessibilityTraitButton;}_message.text=@"暂未读到蜂窝状态，点按重试";_message.hidden=NO;}
    for(NINGCRRow *row in _rows)row.userInteractionEnabled=YES;
}
- (void)choose:(NINGCRRow *)row {
    if(![self isCurrentSession]||_readback.busy)return;NSArray *fresh=NINGCRReadChoices(self.backend);
    if(![self isCurrentSession]||_readback.busy)return;NINGCRChoice *target=nil;for(NINGCRChoice *choice in fresh)if(choice.generation==row.generation){target=choice;break;}
    if(!target||!NINGCRSelectedGeneration(fresh)){[self startReadbackForGeneration:0 item:nil];return;}
    [self renderChoices:fresh];if(target.selected){_heading.text=@"蜂窝4/5G切换";return;}
    [self startReadbackForGeneration:target.generation item:target.nativeItem];
}
- (void)retryMessage:(UITapGestureRecognizer *)gesture {if(_expanded&&_sessionActive)[self refresh];}
@end

@interface NINGCRModule : NSObject <CCUIContentModule>
@property(nonatomic,strong) NINGCRController *controller;
@property(nonatomic,strong) CCUIContentModuleContext *contentModuleContext;
@end
@implementation NINGCRModule
- (UIViewController<CCUIContentModuleContentViewController> *)contentViewController {if(!_controller){_controller=[NINGCRController new];_controller.moduleContext=self.contentModuleContext;}return _controller;}
- (void)setContentModuleContext:(CCUIContentModuleContext *)context {_contentModuleContext=context;_controller.moduleContext=context;}
- (UIViewController *)backgroundViewController{return nil;}
@end
