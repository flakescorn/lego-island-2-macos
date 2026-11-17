/* Integration probe of the real runtime, linked with non-game declarations only. */
#include <stdlib.h>
#include <assert.h>
#include <sys/stat.h>
#include "runtime.h"
#include "options.h"
#include "win.h"
#include "vk.h"
int main(int argc, char **argv) {
    snprintf(user_dir,1024,"work/smoke-user"); mkdir(user_dir,0700);
    mem_init(); options_load(); deterministic = 1;
    option_set("render_thread","off");
    int window = argc > 1;
    headless = !window;
    if (window) { win_init(); host_window_create("LEGO Island 2 runtime probe",640,480); }
    else setenv("LI2_GPU_OFFSCREEN","1",1);
    setenv("LI2_DUMP_FRAMES", window ? "work/smoke-window-frames" : "work/smoke-offscreen-frames",1);
    setenv("LI2_DUMP_EVERY","1",1);
    if (!vk_on()) { fprintf(stderr,"FAIL: runtime Vulkan initialization\n"); return 1; }
    puts("PASS: actual runtime initialized MoltenVK (not a game/menu test)");
    Surface surface = {.id=1,.caps=DDSCAPS_3DDEVICE,.width=64,.height=64,.pitch=256,.bpp=4,
        .pf={32,DDPF_RGB,0,32,0xff0000,0xff00,0xff,0},.shift={16,8,0,24},.bits={8,8,8,0},
        .memsize=64*64*4};
    surface.mem = galloc(surface.memsize);
    for (int i=0;i<256;i++) gfx_gamma[0][i]=gfx_gamma[1][i]=gfx_gamma[2][i]=(uint16_t)(i*257);
    vk_fill(&surface,NULL,0x336699);
    D3DState state = {.rt=&surface,.vp={0,0,64,64,0,1}};
    state.rs[RS_CULLMODE]=1; state.rs[RS_FILLMODE]=3; state.rs[RS_SHADEMODE]=2;
    state.tss[0][TSS_COLOROP]=2; state.tss[0][TSS_COLORARG1]=0;
    state.tss[0][TSS_ALPHAOP]=2; state.tss[0][TSS_ALPHAARG1]=0;
    state.tss[1][TSS_COLOROP]=1;
    SwVertex vertices[3] = {
        {.x=8,.y=8,.z=.5f,.w=1,.diffuse={1,0,0,1}},
        {.x=56,.y=8,.z=.5f,.w=1,.diffuse={1,0,0,1}},
        {.x=32,.y=56,.z=.5f,.w=1,.diffuse={1,0,0,1}}};
    vk_draw(&state,PT_TRIANGLELIST,vertices,3,NULL,0,1);
    vk_present(&surface,NULL);
    vk_sync();
    vk_cpu_access(&surface,0);
    assert((R32(surface.mem) & 0xffffff) == 0x336699);
    assert((R32(surface.mem + 32*256 + 32*4) & 0xffffff) == 0xff0000);
    puts("PASS: runtime GPU fill/triangle/present/readback preserved expected RGB pixels");
    vk_surface_destroyed(&surface);
    vk_stop();
    return 0;
}
