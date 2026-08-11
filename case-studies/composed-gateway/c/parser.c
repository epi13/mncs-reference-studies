#include "parser.h"

int mncs_parse_u32(const uint8_t *data, size_t len, uint32_t *out) {
    if (!data || !out || len == 0 || len > 6) return 1;
    uint32_t value = 0;
    for (size_t index = 0; index < len; index++) {
        if (data[index] < '0' || data[index] > '9') return 2;
        uint32_t digit = (uint32_t)(data[index] - '0');
        if (value > (100000u - digit) / 10u) return 3;
        value = value * 10u + digit;
    }
    *out = value;
    return 0;
}
