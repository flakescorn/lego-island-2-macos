#include <errno.h>
#include <sys/mman.h>
#include <unistd.h>
#include "runtime.h"

#ifdef __APPLE__
uint8_t *guest_memory;
#endif
uint32_t guest_page_size(void) { return (uint32_t)getpagesize(); }
void *guest_map(void *address, size_t size, int prot)
{
#ifdef __APPLE__
    if (!guest_memory) {
        /* Reserve all 32-bit offsets, without claiming any fixed host address or page-zero. */
        guest_memory = mmap(NULL, UINT64_C(0x100000000), PROT_NONE,
                            MAP_PRIVATE | MAP_ANON | MAP_NORESERVE, -1, 0);
        if (guest_memory == MAP_FAILED) fatal("cannot reserve 4 GB guest address space: %s", strerror(errno));
        address = (void *)((uintptr_t)guest_memory + (uintptr_t)address);
    }
    size_t page = guest_page_size();
    uintptr_t start = (uintptr_t)address & ~(page - 1);
    size_t length = (((uintptr_t)address + size + page - 1) & ~(page - 1)) - start;
    if (start < (uintptr_t)guest_memory || length > UINT64_C(0x100000000) ||
        start - (uintptr_t)guest_memory > UINT64_C(0x100000000) - length) {
        errno = EINVAL;
        return MAP_FAILED;
    }
    if (mprotect((void *)start, length, prot)) return MAP_FAILED;
    return address;
#else
    return mmap(address, size, prot, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE | MAP_FIXED_NOREPLACE, -1, 0);
#endif
}
void guest_discard(uint32_t address, size_t size)
{
#ifdef __APPLE__
    /* MADV_DONTNEED on Darwin does not promise zero-filled contents, unlike Linux.
       Windows decommit/recommit requires zeros. Guest pages can be 4 KB on a 16 KB host. */
    memset((void *)GP(address), 0, size);
#else
    madvise((void *)GP(address), size, MADV_DONTNEED);
#endif
}

int host_sleep_until(const struct timespec *deadline)
{
    for (;;) {
        struct timespec now, delay;
        if (clock_gettime(CLOCK_MONOTONIC, &now)) return errno;
        delay.tv_sec = deadline->tv_sec - now.tv_sec;
        delay.tv_nsec = deadline->tv_nsec - now.tv_nsec;
        if (delay.tv_nsec < 0) { delay.tv_sec--; delay.tv_nsec += 1000000000L; }
        if (delay.tv_sec < 0 || (!delay.tv_sec && !delay.tv_nsec)) return 0;
        if (!nanosleep(&delay, NULL)) return 0;
        if (errno != EINTR) return errno;
    }
}
