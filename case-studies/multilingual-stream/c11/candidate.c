#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define MAX_INPUT 1048576u
#define MAX_VALUE 100000u
#define PRIME 16777619u

static unsigned char input[MAX_INPUT + 1u];

static int invalid(void) {
    fputs("invalid input\n", stderr);
    return 2;
}

int main(void) {
    size_t length = fread(input, 1u, sizeof input, stdin);
    if (ferror(stdin) || length > MAX_INPUT || (!feof(stdin) && length == sizeof input)) {
        return invalid();
    }
    uint64_t count = 0u;
    uint64_t sum = 0u;
    uint32_t checksum = 0u;
    uint32_t value = 0u;
    unsigned int digits = 0u;
    size_t i = 0u;
    while (i < length) {
        unsigned char byte = input[i];
        if (byte >= (unsigned char)'0' && byte <= (unsigned char)'9') {
            if (digits >= 10u || value > (MAX_VALUE - (uint32_t)(byte - (unsigned char)'0')) / 10u) {
                return invalid();
            }
            value = value * 10u + (uint32_t)(byte - (unsigned char)'0');
            digits += 1u;
            i += 1u;
            continue;
        }
        if (byte == (unsigned char)'\r' && i + 1u < length && input[i + 1u] == (unsigned char)'\n') {
            i += 2u;
        } else if (byte == (unsigned char)'\n') {
            i += 1u;
        } else {
            return invalid();
        }
        if (digits == 0u || count == UINT64_MAX || sum > UINT64_MAX - (uint64_t)value) {
            return invalid();
        }
        count += 1u;
        sum += (uint64_t)value;
        checksum = (uint32_t)(checksum * PRIME) ^ value;
        value = 0u;
        digits = 0u;
    }
    if (digits != 0u) {
        if (count == UINT64_MAX || sum > UINT64_MAX - (uint64_t)value) {
            return invalid();
        }
        count += 1u;
        sum += (uint64_t)value;
        checksum = (uint32_t)(checksum * PRIME) ^ value;
    }
    printf("{\"count\":%" PRIu64 ",\"sum\":%" PRIu64 ",\"checksum\":%" PRIu32 "}\n", count, sum, checksum);
    return 0;
}
