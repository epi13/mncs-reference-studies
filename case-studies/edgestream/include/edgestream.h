#ifndef EDGESTREAM_H
#define EDGESTREAM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ES_MAX_DEVICES 64u
#define ES_MAX_METRICS 4u
#define ES_WINDOW_SAMPLES 8u
#define ES_MAX_FRAME_SIZE 32u
#define ES_MAX_BUFFER 4096u
#define ES_SILENCE_MS 60000ull

#define ES_FLAG_RESTART 0x01u
#define ES_METRIC_WATERMARK 0xffffu

typedef struct {
    uint32_t values[ES_WINDOW_SAMPLES];
    uint8_t count;
    uint8_t next;
    bool high_alarm;
} es_metric_state;

typedef struct {
    bool used;
    bool seq_valid;
    bool silence_alarm;
    uint32_t device_id;
    uint32_t last_seq;
    uint64_t last_timestamp;
    es_metric_state metrics[ES_MAX_METRICS];
} es_device_state;

typedef struct {
    uint8_t buffer[ES_MAX_BUFFER];
    size_t buffered;
    es_device_state devices[ES_MAX_DEVICES];
    uint64_t accepted;
    uint64_t rejected;
    bool quiet;
} es_processor;

void es_init(es_processor *processor, bool quiet);
int es_process_bytes(es_processor *processor, const uint8_t *data, size_t length, FILE *output);
int es_finish(es_processor *processor, FILE *output);
int es_checkpoint(es_processor *processor, const char *path, FILE *output, int fail_step);
int es_restore(es_processor *processor, const char *path, FILE *output);
const char *es_implementation_name(void);

#endif
