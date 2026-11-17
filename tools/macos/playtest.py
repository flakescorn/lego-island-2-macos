#!/usr/bin/env python3
"""Reproducible Version 1 smoke scenes using the runtime's real DirectInput script path.
All saves/dumps/logs stay in work/. These checks do not establish full-game compatibility.
"""
import argparse,os,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
p=argparse.ArgumentParser();p.add_argument('scene',choices=['menu','town','controls','save-menu','save','load','jump']);p.add_argument('--game',default='work/private-extracted/Game');a=p.parse_args()
keys='1900:RETURN,2100:RETURN'
frames={'menu':1800,'town':8800,'controls':9500,'save-menu':10000,'save':10500,'load':8500,'jump':9140}[a.scene]
if a.scene=='menu':keys=''
if a.scene=='jump':keys+=',8800:UP*120,9100:LMENU*10'
if a.scene=='load':keys='1900:RETURN,2000:DOWN,2100:RETURN,2300:RETURN,2400:DOWN,2500:RETURN'
if a.scene in ['controls','save-menu','save']:keys+=',8800:UP*120,9100:LCONTROL*5,9400:ESCAPE'
if a.scene in ['save-menu','save']:keys+=',9500:DOWN,9600:DOWN,9700:RETURN'
if a.scene=='save':keys+=',10000:RETURN,10100:DOWN,10200:RETURN'
folder=root/('work/v1-'+a.scene+'-test');folder.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,LI2_GPU_OFFSCREEN='1',LI2_TEST_FPS='30',LI2_KEYS=keys,
         LI2_DUMP_FRAMES=str(folder/'frames'),LI2_DUMP_EVERY='5' if a.scene=='jump' else '100',LI2_DUMP_FROM='9100' if a.scene=='jump' else str(max(0,frames-1000)),MVK_CONFIG_LOG_LEVEL='1')
with (folder/'console.log').open('w') as log:
    r=subprocess.run(['build/li2','--game',str(pathlib.Path(a.game).resolve()),'--user',str(root/'work/v1-test-user'),
        '--test','--log','file','--frames',str(frames),'--logfile',str(folder/'run.log')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
print('Exit',r.returncode,'; logs and frames:',folder)
raise SystemExit(r.returncode)
