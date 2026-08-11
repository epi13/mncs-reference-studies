#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_INPUT 1048576u
#define MAX_VALUE 100000u
#define PRIME 16777619u

static int invalid(void) {
    fputs("invalid input\n", stderr);
    return 2;
}

int main(void) {
    char line[32];
    uint64_t count = 0u;
    uint64_t sum = 0u;
    uint32_t checksum = 0u;
    size_t total = 0u;
    while (fgets(line, sizeof line, stdin) != NULL) {
        size_t len = strlen(line);
        total += len;
        if (total > MAX_INPUT || len == 0u || strchr(line, '\0') == NULL) {
            return invalid();
        }
        if (line[len - 1u] == '\n') {
            line[--len] = '\0';
            if (len > 0u && line[len - 1u] == '\r') {
                line[--len] = '\0';
            }
        } else if (!feof(stdin)) {
            return invalid();
        }
        if (len == 0u) {
            return invalid();
        }
        for (size_t i = 0u; i < len; ++i) {
            if (line[i] < '0' || line[i] > '9') {
                return invalid();
            }
        }
        errno = 0;
        char *end = NULL;
        unsigned long value = strtoul(line, &end, 10);
        if (errno != 0 || end == line || *end != '\0' || value > MAX_VALUE) {
            return invalid();
        }
        if (count == UINT64_MAX || sum > UINT64_MAX - (uint64_t)value) {
            return invalid();
        }
        count += 1u;
        sum += (uint64_t)value;
        checksum = (uint32_t)(checksum * PRIME) ^ (uint32_t)value;
    }
    if (ferror(stdin)) {
        return invalid();
    }
    printf("{\"count\":%" PRIu64 ",\"sum\":%" PRIu64 ",\"checksum\":%" PRIu32 "}\n", count, sum, checksum);
    return 0;
}
