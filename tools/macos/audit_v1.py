#!/usr/bin/env python3
"""Check every configured Version 1 patch against the user's exact executable.
Uses Capstone instruction boundaries and original operands, plus PE code-pointer tables.
Writes only addresses/check results to its report; input files are never patched.
"""
import hashlib,importlib.util,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools'))
from pe import PE
from image import Image,Module,Decoder
from discover import Discovery

def audit(folder):
    sp=importlib.util.spec_from_file_location('cfg',root/'builds/en_v1.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
    exe=pathlib.Path(folder)/'LEGO Island 2.exe'
    assert hashlib.sha256(exe.read_bytes()).hexdigest()==c.MODULES[0][2], 'wrong executable hash'
    p=Image([Module(c.MODULES[0][0],str(exe))]);d=Decoder(p)
    disc=Discovery(p,d,{a:n for dll,n,a in p.imports},c.NORETURN_IMPORTS,[],{},[])
    funcs=disc.run(p.seeds(),p.data_code_pointers());sites={a for f in funcs.values() for a in f.insns}
    errors=[];checks=[]
    def check(ok,kind,a,detail):
        checks.append(dict(kind=kind,address=hex(a),passed=bool(ok),detail=detail))
        if not ok:errors.append(checks[-1])
    for a,name in c.HOOKS.items():check(a in funcs,'hook',a,name)
    for a in c.TICKS:check(a in funcs,'tick',a,'30 Hz function')
    for name,(a,operand) in c.MEM_OVERRIDES.items():
        i=d.at(a);check(a in sites and i and any(op[0]=='m' and op[-1]==operand for op in i.ops),'memory operand',a,name)
    for name,v in c.CONSTS.items():
        for a in v['insns']:
            i=d.at(a);check(a in sites and i and any(op[0]=='i' and op[1]==v['value'] for op in i.ops),'literal',a,name)
    for a,kind in c.FRAME_STEPS.items():check(a in sites,'frame step',a,kind)
    for a,kind in c.FRAME_COUNTS.items():check(a in sites,'frame count',a,kind)
    pe=p.main.pe
    check(pe.u32(0x88f8b0)==0x7a87f3,'front-end state table',0x88f8b0,'z00FRE points at the mapped frontend')
    # Verify CD-hook globals from the real instructions, not a blanket data offset.
    check(pe.u32(0x4083d1)==0x8927a8,'CD-check entry operand',0x4083d0,'original drive-check state')
    check(pe.u32(0x40847f)==0x975d38,'game directory operand',0x40847e,'Version 1 CD path')
    check(pe.u32(0x4084b0)==0x9764d4,'movie directory operand',0x4084af,'Version 1 movie directory')
    check(pe.u32(0x81c731)==0x5d516f0,'movie skip flag',0x81c730,'Version 1 movie skippability')
    result=dict(version=c.NAME,functions=len(funcs),instructions=sum(len(f.insns) for f in funcs.values()),checks=checks,errors=errors)
    out=root/'work/v1-address-audit.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print('%d functions; %d address checks; %d failures; report %s'%(len(funcs),len(checks),len(errors),out),flush=True)
    for e in errors:print(e,flush=True)
    return not errors
if __name__=='__main__':sys.exit(0 if audit(sys.argv[1]) else 1)
