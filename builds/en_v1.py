"""Original PC English Version 1 (identifier 0x52), address-only configuration.

Run the game's own translated functions. Version 2's hand-written skinning, native
renderer hooks and per-instruction timing patches have separate address assumptions
and are intentionally not enabled for this build. Initial play runs at 30 fps.
"""
NAME = 'en-v1'
MODULES = [('LEGO Island 2.exe', 'LEGO Island 2.exe',
            '117c111d8de6ce6179c70b2ff88f74766a3417b9997e83b186e1c56fca873198')]
EXTRA_ENTRIES = []
NOT_ENTRIES = []
JUMP_TABLES = {}
NONLOCAL_JUMPS = []
NORETURN_IMPORTS = ['ExitProcess','ExitThread','TerminateProcess','FatalExit','FatalAppExitA']
# Verified against Version 1's disassembly: CD drive check and cdecl loading present.
HOOKS = {0x4083d0:'cd_check', 0x42a870:'loading_frame'}
MEM_OVERRIDES = {}
CONSTS = {}
FRAME_STEPS = {}
FRAME_COUNTS = {}
TICKS = []
FPSCHECK_REVIEWED = {}
