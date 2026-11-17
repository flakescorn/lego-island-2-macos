/* Guest addresses stay 32-bit even when host pointers are above 4 GB. */
#pragma once
#include <stddef.h>
#include <stdint.h>
void *guest_map(void *address, size_t size, int prot);
uint32_t guest_page_size(void);
void guest_discard(uint32_t address, size_t size);

#include <time.h>
int host_sleep_until(const struct timespec *deadline);
static inline void host_cpu_relax(void) {
#if defined(__aarch64__)
    __asm__ volatile("yield");
#elif defined(__x86_64__) || defined(__i386__)
    __builtin_ia32_pause();
#else
    __asm__ volatile("" ::: "memory");
#endif
}
