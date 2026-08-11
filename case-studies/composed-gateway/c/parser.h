#ifndef MNCS_PARSER_H
#define MNCS_PARSER_H
#include <stddef.h>
#include <stdint.h>
#define MNCS_PARSER_ABI 1u
int mncs_parse_u32(const uint8_t *data, size_t len, uint32_t *out);
#endif
