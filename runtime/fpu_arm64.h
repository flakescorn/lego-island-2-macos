/* Experimental ARM64 x87 helpers. Host arithmetic has 53-bit precision on Apple ARM64;
   this backend is NOT a bit-exact x87 emulator. The 10-byte memory format is preserved. */
#pragma once
#include <stdint.h>
int64_t arm_fpu_int(long double value, int bits, int truncate);
uint16_t arm_fpu_status(void);
