#!/usr/bin/env python3
"""Compile/link the real runtime against non-game declarations and run macOS probes.
The fixture deliberately has no game functions; accidentally calling one aborts.
"""
import importlib.util, os, pathlib, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
if sys.platform!='darwin' or os.uname().machine!='arm64':sys.exit('Run on an ARM64 Mac.')
sp=importlib.util.spec_from_file_location('cfg','builds/en_v2.py');cfg=importlib.util.module_from_spec(sp);sp.loader.exec_module(cfg)
d=root/'work/runtime-check';d.mkdir(parents=True,exist_ok=True)
s='#pragma once\n#include "cpu.h"\n'
fixture='#include "runtime.h"\n#include "funcs.h"\n'
for kind,values in [('rc',cfg.CONSTS),('rm',cfg.MEM_OVERRIDES)]:
    for n,v in values.items():
        s+='extern uint32_t %s_%s;\n'%(kind,n)
        fixture+='uint32_t %s_%s = %du;\n'%(kind,n,v['value'] if kind=='rc' else v[1])
for a,n in cfg.HOOKS.items():
    s+='extern int (*hook_%s)(CPU *c);\nvoid F_%08x_orig(CPU *c);\n'%(n,a)
    fixture+='int (*hook_%s)(CPU *c);\nvoid F_%08x_orig(CPU *c) { fatal("asset-free test called game fixture"); }\n'%(n,a)
for t in ['Func','Import','Link','Module']:
    fixture+='const %sEntry %s_table[]={{0}}; const int %s_count=0;\n'%(t,t.lower(),t.lower())
fixture+='const TableEntry table_list[]={{0}};\n'
(d/'funcs.h').write_text(s);(d/'fixture.c').write_text(fixture)
(d/'image.h').write_text('#pragma once\n#define IMAGE_BASE 0x400000u\n#define IMAGE_SIZE 0x5a8a000u\n#define IMAGE_ENTRY 0x400000u\n#define STACK_RESERVE 0x100000u\n#define MODULE_COUNT 1\n#define BUILD_NAME "asset-free-test-fixture"\n')
flags=['clang','-std=gnu11','-O1','-g','-fno-strict-aliasing','-frounding-math','-ffp-contract=off',
       '-Iruntime','-I'+str(d),'-Ithird_party/sdl3/include','-Ithird_party/simde-0.8.2',
       '-Ithird_party/Vulkan-Headers-vulkan-sdk-1.4.350.1/include','-DDM_STATIC=1','-DDM_BUILD=1',
       '-Ithird_party/dmusic/include','-Ithird_party/dmusic/src','-Ithird_party/dmusic/vendor/TinySoundFont']
sources=[p for p in pathlib.Path('runtime').glob('*.c') if p.name!='game_v1.c']
dm=pathlib.Path('third_party/dmusic')
sources += [p for p in (dm/'src').rglob('*.c') if not p.name.startswith('Thread.')]
sources += [dm/'src/thread/Thread.Posix.c',dm/'vendor/TinySoundFont/tsf.c']
def build(p):
    obj=d/(str(p).replace('/','_')+'.o')
    cmd=flags+(['-DRUNTIME_NO_MAIN'] if p.name=='main.c' else [])+['-c',str(p),'-o',str(obj)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    (d/(obj.name+'.log')).write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(str(p)+'\n'+r.stderr)
    return str(obj)
with ThreadPoolExecutor(max_workers=4) as ex:objects=list(ex.map(build,sources))
rt_count=sum(p.parent==pathlib.Path('runtime') for p in sources)
print('PASS: compiled %d runtime and %d music-engine C files for ARM64'%(rt_count,len(sources)-rt_count),flush=True)
lib=root/'third_party/MoltenVK/MoltenVK/dynamic/dylib/macOS';sdl=root/'third_party/sdl3/lib'
subprocess.run(flags+['tests/macos_smoke.c',str(d/'fixture.c')]+objects+['-L'+str(lib),'-lMoltenVK','-L'+str(sdl),'-lSDL3','-lz','-Wl,-rpath,'+str(lib),'-Wl,-rpath,'+str(sdl),'-o',str(d/'macos-smoke')],check=True)
subprocess.run(flags+['tests/macos_core.c','runtime/mem.c','runtime/platform.c','runtime/fpu_arm64.c','-o',str(d/'macos-core')],check=True)
for name,args in [('core',['macos-core']),('offscreen',['macos-smoke']),('window',['macos-smoke','window'])]:
    with (root/('work/macos-'+name+'.log')).open('w') as log:
        subprocess.run([str(d/args[0])]+args[1:],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
    print('PASS: '+name+' probe; see work/macos-'+name+'.log',flush=True)
print('No translated game, game menu, gameplay, audio, controls or game saves were tested.')
