/* Version 1 glue. The original translated game handles menus, skinning, physics,
   camera and controls. Keep Version 2's optional hand-written paths out of this build. */
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "runtime.h"
#include "funcs.h"
#include "options.h"

#define GAME_DIR_VAR 0x975d38u
#define MOVIE_DIR_VAR 0x9764d4u

static int cd_check(CPU *c)
{
    char base[260],root[260],guest[600],host[1200];
    snprintf(base,sizeof base,"%s",gstr(GAME_DIR_VAR));
    snprintf(root,sizeof root,"%s",base);
    size_t n=strlen(root);
    if (n>=6 && !strcasecmp(root+n-6,"_Data\\")) root[n-6]=0;
    W8(MOVIE_DIR_VAR,0);
    const char *folders[]={"Movies\\","fmv\\","CD\\Lego Island 2\\Movies\\"};
    for (size_t i=0;i<sizeof folders/sizeof folders[0];i++) {
        snprintf(guest,sizeof guest,"%s%sLegoSoftware.mpg",root,folders[i]);
        if (path_to_host(guest,host,sizeof host,0)) {
            guest[strlen(guest)-strlen("LegoSoftware.mpg")]=0;
            gstrncpy(MOVIE_DIR_VAR,guest,128);
            break;
        }
    }
    LOG(LOG_ALWAYS,"Version 1 CD check: C:, movies %s",R8(MOVIE_DIR_VAR)?gstr(MOVIE_DIR_VAR):"unavailable");
    c->eax=2; c->ret=R32(c->esp); c->esp+=4;
    return 1;
}

static int loading_frame(CPU *c)
{
    extern double host_ms(void);
    static double last;
    if (deterministic || !option_bool("fast_loading",1)) return 0;
    double t=host_ms();
    if (t-last>=33) { last=t; return 0; }
    c->ret=R32(c->esp); c->esp+=4;
    return 1;
}

void game_init(void)
{
    hook_cd_check=cd_check;
    hook_loading_frame=loading_frame;
    if (!strcmp(option_str("frame_limit","unset"),"unset")) option_set("frame_limit","30");
    LOG(LOG_ALWAYS,"Version 1: original translated game paths, 30 fps default; ARM x87 precision remains experimental");
}
uint32_t game_movie_skip_flag(void) { return 0x5d516f0u; }
void game_frame(unsigned long frame) { extern void mss_frame(void); (void)frame; mss_frame(); }
void camera_tilt_set(int percent) { (void)percent; }
int prompt_context(void) { return 0; }
int game_driving(void) { return 0; }
void frame_rate_reapply(void) {}
void padgame_frame(unsigned long frame) { (void)frame; }
int ifc_rumble_wanted(void) { return 0; }
void ifc_frame(unsigned long frame) { (void)frame; }
