/* No game data: exercise the real allocator, high host pointers, 16 KB pages and x87 ABI. */
#include <assert.h>
#include <fenv.h>
#include <math.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include "runtime.h"
unsigned log_mask;
void logmsg(unsigned c, const char *f, ...) { (void)c; (void)f; }
void fatal(const char *f, ...) { va_list a; va_start(a,f); vfprintf(stderr,f,a); va_end(a); abort(); }
int main(void) {
    mem_init();
    assert(GP(0x400000) > UINT32_MAX);
    assert(guest_map((void *)GP(0x400000), 0x10000, PROT_READ|PROT_WRITE) == (void *)GP(0x400000));
    W32(0x400001, 0x12345678); assert(R32(0x400001) == 0x12345678);
    uint32_t a = vm_alloc(0, 0x3000, 0); assert(a);
    W32(a, 42); W32(a + 0x2000, 66);
    assert(vm_free(a + 0x1000, 0x1000, 0)); assert(R32(a) == 42 && R32(a + 0x2000) == 66);
    assert(vm_free(a, 0, 1)); assert(vm_alloc(a, 0x3000, 0) == a); assert(R32(a) == 0);
    uint32_t h = heap_create(0,0), b = heap_alloc(h, 73, 1); assert(b && R32(b) == 0);
    W32(b,99); b = heap_realloc(h,b,200,1,0); assert(R32(b) == 99); assert(heap_free(h,b)); assert(heap_destroy(h));
    uint32_t t = vm_alloc_table(70000); W8(t + 69999, 1);
    pid_t child = fork(); assert(child >= 0);
    if (!child) { W8(t + 70000, 1); _exit(0); }
    int status; waitpid(child, &status, 0); assert(WIFSIGNALED(status));
    CPU state = {0}, *c = &state; fpu_init(c);
    assert(fpu_ist32(2.5L) == 2 && fpu_ist32(3.5L) == 4);
    fpu_setcw(c, 0x77f); assert(fpu_ist32(2.9L) == 2 && fpu_ist32(-2.1L) == -3);
    assert(fpu_ftol(-2.9L) == -2); assert(fpu_ftol(INFINITY) == INT64_MIN);
    fpu_init(c);
    long double vals[] = {0.L,-0.L,1.L,-1.5L,0x1p-1022L,INFINITY,-INFINITY,NAN};
    for (unsigned i=0;i<sizeof vals/sizeof vals[0];i++) {
        W8(a+10,0x55); WF80(a,vals[i]); long double r=RF80(a);
        assert(R8(a+10)==0x55); assert(isnan(vals[i]) ? isnan(r) : r==vals[i] && !!signbit(r)==!!signbit(vals[i]));
    }
    FPUSH(2); FPUSH(5); fpu_fprem(c); assert(ST(0)==1); fpu_init(c);
    FPUSH(0); fpu_fsincos(c); assert(ST(0)==1 && ST(1)==0);
    puts("PASS: high-address guest memory, unaligned access, zero-on-free, heap, table guard, ARM x87 helpers/80-bit memory ABI");
    puts("LIMIT: ARM arithmetic uses 53-bit significands; x87 arithmetic fidelity is unverified.");
}
