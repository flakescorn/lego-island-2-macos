#if defined(__aarch64__)
#include <fenv.h>
#include <float.h>
#include <limits.h>
#include <math.h>
#include "runtime.h"
#pragma STDC FENV_ACCESS ON
int fpu_sw_exceptions = 1;
static const int rounds[] = {FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO};
void fpu_setcw(CPU *c, uint32_t cw) { c->fcw = (uint16_t)cw; fesetround(rounds[(cw >> 10) & 3]); }
void fpu_new(CPU *c) { c->ftop = c->fsw = 0; memset(c->st, 0, sizeof c->st); c->fcw = 0x37f; c->mxcsr = 0x1f80; }
void fpu_activate(CPU *c) { fpu_setcw(c, c->fcw); }
void cpu_ldmxcsr(CPU *c, uint32_t v) { c->mxcsr = v & 0xffff; fesetround(rounds[(v >> 13) & 3]); }
void fpu_init(CPU *c) { uint32_t mxcsr = c->mxcsr; fpu_new(c); c->mxcsr = mxcsr; feclearexcept(FE_ALL_EXCEPT); fpu_activate(c); }
void fpu_clex(CPU *c) { (void)c; feclearexcept(FE_ALL_EXCEPT); }
uint16_t arm_fpu_status(void) {
    int f = fetestexcept(FE_ALL_EXCEPT);
    return ((f & FE_INVALID) ? 1 : 0) | ((f & FE_DIVBYZERO) ? 4 : 0) |
           ((f & FE_OVERFLOW) ? 8 : 0) | ((f & FE_UNDERFLOW) ? 16 : 0) | ((f & FE_INEXACT) ? 32 : 0);
}
int64_t arm_fpu_int(long double v, int bits, int truncate) {
    long double r = truncate ? truncl(v) : rintl(v), bound = ldexpl(1, bits - 1);
    if (!isfinite(r) || r < -bound || r >= bound) {
        feraiseexcept(FE_INVALID);
        return bits == 64 ? INT64_MIN : -(INT64_C(1) << (bits - 1));
    }
    return (int64_t)r;
}
long double fpu_read80(const void *p) {
    uint64_t sig; uint16_t se; memcpy(&sig, p, 8); memcpy(&se, (const char *)p + 8, 2);
    unsigned e = se & 0x7fff;
    long double v = e == 0x7fff ? ((sig & UINT64_C(0x7fffffffffffffff)) ? NAN : INFINITY)
                              : ldexpl((long double)sig, (e ? (int)e : 1) - 16383 - 63);
    return se & 0x8000 ? -v : v;
}
void fpu_write80(void *p, long double v) {
    uint64_t sig = 0; uint16_t se = signbit(v) ? 0x8000 : 0;
    if (isnan(v)) { se |= 0x7fff; sig = UINT64_C(0xc000000000000000); }
    else if (isinf(v)) { se |= 0x7fff; sig = UINT64_C(0x8000000000000000); }
    else if (v != 0) { int e; long double f = frexpl(fabsl(v), &e); se |= (uint16_t)(e - 1 + 16383); sig = (uint64_t)ldexpl(f, 64); }
    memcpy(p, &sig, 8); memcpy((char *)p + 8, &se, 2);
}
void fpu_xam(CPU *c) {
    long double v = ST(0); uint16_t cc = signbit(v) ? 0x200 : 0;
    if (isnan(v)) cc |= 0x100; else if (isinf(v)) cc |= 0x500;
    else if (v == 0) cc |= 0x4000; else if (fpclassify(v) == FP_SUBNORMAL) cc |= 0x4400; else cc |= 0x400;
    c->fsw = (c->fsw & ~0x4700) | cc;
}
void fpu_ldconst(CPU *c, int which) {
    static const long double values[] = {1.L, 3.32192809488736234787L, 1.44269504088896340736L,
        3.14159265358979323846L, 0.30102999566398119521L, 0.69314718055994530942L};
    FPUSH(values[which >= 0 && which < 6 ? which : 5]);
}
void fpu_f2xm1(CPU *c) { ST(0) = expm1l(ST(0) * logl(2)); }
void fpu_fyl2x(CPU *c) { long double r = ST(1) * log2l(ST(0)); FPOP(); ST(0) = r; }
void fpu_fyl2xp1(CPU *c) { long double r = ST(1) * (log1pl(ST(0)) / logl(2)); FPOP(); ST(0) = r; }
void fpu_fpatan(CPU *c) { long double r = atan2l(ST(1), ST(0)); FPOP(); ST(0) = r; }
static int trig_range(CPU *c) {
    if (isfinite(ST(0)) && fabsl(ST(0)) >= 0x1p63L) { c->fsw |= 0x400; return 0; }
    c->fsw &= ~0x400; return 1;
}
void fpu_fptan(CPU *c) { if (trig_range(c)) { ST(0) = tanl(ST(0)); FPUSH(1); } }
void fpu_fsincos(CPU *c) { if (trig_range(c)) { long double x = ST(0); ST(0) = sinl(x); FPUSH(cosl(x)); } }
void fpu_fsin(CPU *c) { if (trig_range(c)) ST(0) = sinl(ST(0)); }
void fpu_fcos(CPU *c) { if (trig_range(c)) ST(0) = cosl(ST(0)); }
void fpu_fscale(CPU *c) { long double e = truncl(ST(1)); if (isnan(e)) { ST(0) = e; return; } ST(0) = scalbnl(ST(0), e > 32768 ? 32768 : e < -32768 ? -32768 : (int)e); }
void fpu_fxtract(CPU *c) {
    long double x = ST(0), sig, ex;
    if (x == 0) { sig = x; ex = -INFINITY; feraiseexcept(FE_DIVBYZERO); }
    else if (!isfinite(x)) { sig = x; ex = isnan(x) ? x : INFINITY; }
    else { int e; sig = frexpl(x, &e) * 2; ex = e - 1; }
    ST(0) = ex; FPUSH(sig);
}
static void prem(CPU *c, int nearest) {
    long double x = ST(0), y = ST(1);
    int ex = 0, ey = 0; frexpl(x, &ex); frexpl(y, &ey);
    if (isfinite(x) && isfinite(y) && y != 0 && ex - ey >= 64) {
        long double scale = scalbnl(y, ex - ey - 32);
        ST(0) = fmodl(x, scale); c->fsw |= 0x400; return;
    }
    long double r = nearest ? remainderl(x, y) : fmodl(x, y);
    long double q = (x - r) / y;
    unsigned b = isfinite(q) ? (unsigned)(int)fmodl(q, 8) & 7 : 0;
    c->fsw = (c->fsw & ~0x4700) | ((b & 4) ? 0x100 : 0) | ((b & 2) ? 0x4000 : 0) | ((b & 1) ? 0x200 : 0);
    ST(0) = r;
}
void fpu_fprem(CPU *c) { prem(c, 0); }
void fpu_fprem1(CPU *c) { prem(c, 1); }
void cpu_cpuid(CPU *c)
{
    uint32_t leaf = c->eax;
    c->ecx = 0;
    switch (leaf) {
    case 0:
        c->eax = 2;
        c->ebx = 0x756e6547u;           /* "Genu" */
        c->edx = 0x49656e69u;           /* "ineI" */
        c->ecx = 0x6c65746eu;           /* "ntel" */
        break;
    case 1:
        c->eax = 0x686;
        c->ebx = 0;
        c->edx = 0x0383f9ffu;           /* FPU ... CMOV, PAT, PSE36, MMX, FXSR, SSE */
        break;
    case 2:
        c->eax = 0x03020101u;
        c->ebx = 0;
        c->edx = 0x0c040882u;
        break;
    default:
        c->eax = leaf >= 0x80000000u ? 0x80000000u : 0;   /* no extended leaves */
        c->ebx = c->edx = 0;
        break;
    }
}

/* 28-byte protected-mode environment: CW, SW, TW, then instruction/operand pointers. */
void fpu_stenv(CPU *c, uint32_t a)
{
    W32(a, c->fcw | 0xffff0000u);
    W32(a + 4, fpu_sw(c) | 0xffff0000u);
    W32(a + 8, 0xffffffffu);
    for (int i = 12; i < 28; i += 4)
        W32(a + i, 0);
}

void fpu_ldenv(CPU *c, uint32_t a)
{
    fpu_setcw(c, R16(a));
    uint16_t sw = (uint16_t)R16(a + 4);
    c->fsw = sw & 0x4700;
    c->ftop = (sw >> 11) & 7;
}

void fpu_save(CPU *c, uint32_t a)
{
    fpu_stenv(c, a);
    W32(a + 8, 0);                    /* all registers tagged valid */
    for (int i = 0; i < 8; i++)
        WF80(a + 28 + 10 * i, ST(i));
    fpu_init(c);
}

void fpu_rstor(CPU *c, uint32_t a)
{
    fpu_ldenv(c, a);
    for (int i = 0; i < 8; i++)
        ST(i) = RF80(a + 28 + 10 * i);
}

/* Generated code keeping the x87 stack in locals assumed a call through a pointer leaves the
   stack depth as it was (tools/fpustack.py); it did not. */
void fpu_depth_fail(CPU *c, uint32_t at)
{
    fatal("x87 stack depth changed by the call at %08x (top %u): add the callee's effect to the "
          "translator (tools/fpustack.py)", at, c->ftop);
}

#endif
