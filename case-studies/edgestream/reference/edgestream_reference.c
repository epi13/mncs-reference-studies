#include "edgestream.h"

#include <errno.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

#define ES_CHECKPOINT_MAGIC "ESCP"
#define ES_CHECKPOINT_VERSION 1u

static uint16_t read_u16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8u));
}

static uint32_t read_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8u) | ((uint32_t)p[2] << 16u) |
           ((uint32_t)p[3] << 24u);
}

static uint64_t read_u64(const uint8_t *p) {
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) {
        value |= (uint64_t)p[i] << (8u * i);
    }
    return value;
}

static uint32_t crc32_slow(const uint8_t *data, size_t length) {
    uint32_t crc = 0xffffffffu;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1u) ^ (0xedb88320u & mask);
        }
    }
    return ~crc;
}

static void emit(FILE *out, bool quiet, const char *text) {
    if (!quiet) {
        fputs(text, out);
        fputc('\n', out);
    }
}

static void emit_reject(es_processor *p, FILE *out, const char *reason) {
    char line[160];
    p->rejected++;
    (void)snprintf(line, sizeof(line),
                   "{\"type\":\"reject\",\"reason\":\"%s\",\"rejected\":%" PRIu64 "}",
                   reason, p->rejected);
    emit(out, p->quiet, line);
}

static es_device_state *find_device(es_processor *p, uint32_t id, FILE *out) {
    es_device_state *free_slot = NULL;
    for (size_t i = 0; i < ES_MAX_DEVICES; ++i) {
        if (p->devices[i].used && p->devices[i].device_id == id) {
            return &p->devices[i];
        }
        if (!p->devices[i].used && free_slot == NULL) {
            free_slot = &p->devices[i];
        }
    }
    if (free_slot == NULL) {
        char line[160];
        (void)snprintf(line, sizeof(line),
                       "{\"type\":\"resource_limit\",\"resource\":\"active_devices\",\"device\":%u}",
                       id);
        emit(out, p->quiet, line);
        return NULL;
    }
    memset(free_slot, 0, sizeof(*free_slot));
    free_slot->used = true;
    free_slot->device_id = id;
    return free_slot;
}

static void emit_silence(es_processor *p, FILE *out, uint64_t watermark) {
    for (size_t i = 0; i < ES_MAX_DEVICES; ++i) {
        es_device_state *device = &p->devices[i];
        if (!device->used || device->last_timestamp == 0) {
            continue;
        }
        bool silent = watermark > device->last_timestamp &&
                      watermark - device->last_timestamp > ES_SILENCE_MS;
        if (silent && !device->silence_alarm) {
            char line[192];
            device->silence_alarm = true;
            (void)snprintf(line, sizeof(line),
                           "{\"type\":\"alarm\",\"alarm\":\"silence\",\"state\":\"active\",\"device\":%u,\"watermark\":%" PRIu64 "}",
                           device->device_id, watermark);
            emit(out, p->quiet, line);
        }
    }
}

static void accept_frame(es_processor *p, const uint8_t *frame, FILE *out) {
    uint8_t version = frame[2];
    uint8_t flags = frame[3];
    uint32_t device_id = read_u32(frame + 6);
    uint32_t sequence = read_u32(frame + 10);
    uint64_t timestamp = read_u64(frame + 14);
    uint16_t metric = read_u16(frame + 22);
    int32_t raw_value = (int32_t)read_u32(frame + 24);
    int64_t normalized = version == 2 ? (int64_t)raw_value * 10 : raw_value;

    if (metric == ES_METRIC_WATERMARK) {
        emit_silence(p, out, timestamp);
        return;
    }
    if (metric >= ES_MAX_METRICS) {
        emit_reject(p, out, "metric");
        return;
    }

    es_device_state *device = find_device(p, device_id, out);
    if (device == NULL) {
        return;
    }
    if ((flags & ES_FLAG_RESTART) != 0) {
        device->seq_valid = false;
        memset(device->metrics, 0, sizeof(device->metrics));
    }
    if (device->seq_valid) {
        if (sequence == device->last_seq) {
            char line[160];
            (void)snprintf(line, sizeof(line),
                           "{\"type\":\"duplicate\",\"device\":%u,\"sequence\":%u}",
                           device_id, sequence);
            emit(out, p->quiet, line);
            return;
        }
        bool rollover = device->last_seq >= 0xfffffff0u && sequence <= 0x0fu;
        if (!rollover && sequence < device->last_seq) {
            char line[192];
            (void)snprintf(line, sizeof(line),
                           "{\"type\":\"late\",\"device\":%u,\"sequence\":%u,\"last_sequence\":%u}",
                           device_id, sequence, device->last_seq);
            emit(out, p->quiet, line);
            return;
        }
    }

    if (device->silence_alarm) {
        char line[160];
        device->silence_alarm = false;
        (void)snprintf(line, sizeof(line),
                       "{\"type\":\"alarm\",\"alarm\":\"silence\",\"state\":\"clear\",\"device\":%u}",
                       device_id);
        emit(out, p->quiet, line);
    }

    device->seq_valid = true;
    device->last_seq = sequence;
    device->last_timestamp = timestamp;
    es_metric_state *state = &device->metrics[metric];
    state->values[state->next] = (uint32_t)(int32_t)normalized;
    state->next = (uint8_t)((state->next + 1u) % ES_WINDOW_SAMPLES);
    if (state->count < ES_WINDOW_SAMPLES) {
        state->count++;
    }
    int64_t sum = 0;
    for (uint8_t i = 0; i < state->count; ++i) {
        sum += (int32_t)state->values[i];
    }
    int64_t average = sum / state->count;
    p->accepted++;

    char line[256];
    (void)snprintf(line, sizeof(line),
                   "{\"type\":\"event\",\"device\":%u,\"sequence\":%u,\"timestamp\":%" PRIu64 ",\"metric\":%u,\"value_milli\":%" PRId64 ",\"window_average_milli\":%" PRId64 ",\"accepted\":%" PRIu64 "}",
                   device_id, sequence, timestamp, metric, normalized, average, p->accepted);
    emit(out, p->quiet, line);

    bool high = average > 50000;
    bool clear = average <= 45000;
    if (high && !state->high_alarm) {
        state->high_alarm = true;
        (void)snprintf(line, sizeof(line),
                       "{\"type\":\"alarm\",\"alarm\":\"high\",\"state\":\"active\",\"device\":%u,\"metric\":%u,\"average_milli\":%" PRId64 "}",
                       device_id, metric, average);
        emit(out, p->quiet, line);
    } else if (clear && state->high_alarm) {
        state->high_alarm = false;
        (void)snprintf(line, sizeof(line),
                       "{\"type\":\"alarm\",\"alarm\":\"high\",\"state\":\"clear\",\"device\":%u,\"metric\":%u,\"average_milli\":%" PRId64 "}",
                       device_id, metric, average);
        emit(out, p->quiet, line);
    }
}

void es_init(es_processor *p, bool quiet) {
    memset(p, 0, sizeof(*p));
    p->quiet = quiet;
}

int es_process_bytes(es_processor *p, const uint8_t *data, size_t length, FILE *out) {
    if (length > ES_MAX_BUFFER - p->buffered) {
        emit_reject(p, out, "parser_buffer");
        p->buffered = 0;
        return -1;
    }
    memcpy(p->buffer + p->buffered, data, length);
    p->buffered += length;

    size_t offset = 0;
    while (p->buffered - offset >= 2) {
        if (p->buffer[offset] != 0xe5u || p->buffer[offset + 1] != 0x47u) {
            emit_reject(p, out, "junk");
            offset++;
            continue;
        }
        if (p->buffered - offset < 6) {
            break;
        }
        uint16_t frame_length = read_u16(p->buffer + offset + 4);
        if (frame_length != ES_MAX_FRAME_SIZE) {
            emit_reject(p, out, "length");
            offset++;
            continue;
        }
        if (p->buffered - offset < frame_length) {
            break;
        }
        uint8_t version = p->buffer[offset + 2];
        if (version != 1 && version != 2) {
            emit_reject(p, out, "version");
            offset += frame_length;
            continue;
        }
        uint32_t expected = read_u32(p->buffer + offset + 28);
        uint32_t actual = crc32_slow(p->buffer + offset, 28);
        if (expected != actual) {
            emit_reject(p, out, "checksum");
            offset += frame_length;
            continue;
        }
        accept_frame(p, p->buffer + offset, out);
        offset += frame_length;
    }
    if (offset > 0) {
        memmove(p->buffer, p->buffer + offset, p->buffered - offset);
        p->buffered -= offset;
    }
    return 0;
}

int es_finish(es_processor *p, FILE *out) {
    if (p->buffered != 0) {
        emit_reject(p, out, "truncated");
        p->buffered = 0;
        return 1;
    }
    return 0;
}

typedef struct {
    char magic[4];
    uint32_t version;
    uint32_t payload_size;
    uint32_t crc;
} checkpoint_header;

int es_checkpoint(es_processor *p, const char *path, FILE *out, int fail_step) {
    char temporary[1024];
    if (snprintf(temporary, sizeof(temporary), "%s.tmp", path) >= (int)sizeof(temporary)) {
        return -1;
    }
    FILE *file = fopen(temporary, "wb");
    if (file == NULL) {
        return -1;
    }
    checkpoint_header header = {{'E', 'S', 'C', 'P'}, ES_CHECKPOINT_VERSION,
                                (uint32_t)sizeof(*p), crc32_slow((const uint8_t *)p, sizeof(*p))};
    int status = 0;
    if (fail_step == 1 || fwrite(&header, sizeof(header), 1, file) != 1) {
        status = -1;
    } else if (fail_step == 2 || fwrite(p, sizeof(*p), 1, file) != 1) {
        status = -1;
    } else if (fail_step == 3 || fflush(file) != 0) {
        status = -1;
    }
    if (fclose(file) != 0) {
        status = -1;
    }
    if (fail_step == 4) {
        status = -1;
    }
    if (status == 0) {
        if (rename(temporary, path) != 0) {
            status = -1;
        }
    } else {
        (void)remove(temporary);
    }
    char line[160];
    (void)snprintf(line, sizeof(line),
                   "{\"type\":\"checkpoint\",\"status\":\"%s\",\"fail_step\":%d}",
                   status == 0 ? "PASS" : "FAIL", fail_step);
    emit(out, p->quiet, line);
    return status;
}

int es_restore(es_processor *p, const char *path, FILE *out) {
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        return -1;
    }
    checkpoint_header header;
    es_processor restored;
    int status = 0;
    if (fread(&header, sizeof(header), 1, file) != 1 ||
        memcmp(header.magic, ES_CHECKPOINT_MAGIC, 4) != 0 ||
        header.version != ES_CHECKPOINT_VERSION || header.payload_size != sizeof(restored) ||
        fread(&restored, sizeof(restored), 1, file) != 1 ||
        header.crc != crc32_slow((const uint8_t *)&restored, sizeof(restored))) {
        status = -1;
    }
    (void)fclose(file);
    if (status == 0) {
        bool quiet = p->quiet;
        *p = restored;
        p->quiet = quiet;
    }
    char line[128];
    (void)snprintf(line, sizeof(line), "{\"type\":\"recovery\",\"status\":\"%s\"}",
                   status == 0 ? "PASS" : "FAIL");
    emit(out, p->quiet, line);
    return status;
}

const char *es_implementation_name(void) {
    return "reference";
}
