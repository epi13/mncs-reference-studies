#include "edgestream.h"

#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void usage(const char *name) {
    fprintf(stderr,
            "usage: %s [--chunk N] [--quiet] [--checkpoint-in FILE] "
            "[--checkpoint-out FILE] [--fail-checkpoint-step N] INPUT\n",
            name);
}

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        return 0;
    }
    return (uint64_t)value.tv_sec * 1000000000ull + (uint64_t)value.tv_nsec;
}

int main(int argc, char **argv) {
    size_t chunk = 4096;
    bool quiet = false;
    const char *checkpoint_in = NULL;
    const char *checkpoint_out = NULL;
    int fail_step = 0;
    const char *input_path = NULL;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--chunk") == 0 && i + 1 < argc) {
            chunk = (size_t)strtoul(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "--quiet") == 0) {
            quiet = true;
        } else if (strcmp(argv[i], "--checkpoint-in") == 0 && i + 1 < argc) {
            checkpoint_in = argv[++i];
        } else if (strcmp(argv[i], "--checkpoint-out") == 0 && i + 1 < argc) {
            checkpoint_out = argv[++i];
        } else if (strcmp(argv[i], "--fail-checkpoint-step") == 0 && i + 1 < argc) {
            fail_step = atoi(argv[++i]);
        } else if (argv[i][0] != '-') {
            input_path = argv[i];
        } else {
            usage(argv[0]);
            return 2;
        }
    }
    if (input_path == NULL || chunk == 0 || chunk > ES_MAX_BUFFER) {
        usage(argv[0]);
        return 2;
    }

    FILE *input = fopen(input_path, "rb");
    if (input == NULL) {
        fprintf(stderr, "cannot open %s: %s\n", input_path, strerror(errno));
        return 2;
    }
    uint8_t *buffer = malloc(chunk);
    if (buffer == NULL) {
        fclose(input);
        return 2;
    }

    es_processor processor;
    es_init(&processor, quiet);
    if (checkpoint_in != NULL && es_restore(&processor, checkpoint_in, stdout) != 0) {
        free(buffer);
        fclose(input);
        return 3;
    }

    uint64_t started = monotonic_ns();
    size_t bytes = 0;
    int status = 0;
    while (!feof(input)) {
        size_t count = fread(buffer, 1, chunk, input);
        bytes += count;
        size_t delivered = 0;
        while (delivered < count) {
            size_t remaining = count - delivered;
            size_t delivery = remaining < (ES_MAX_BUFFER / 2u) ? remaining : (ES_MAX_BUFFER / 2u);
            if (es_process_bytes(&processor, buffer + delivered, delivery, stdout) != 0) {
                status = 1;
            }
            delivered += delivery;
        }
        if (ferror(input)) {
            status = 2;
            break;
        }
    }
    if (es_finish(&processor, stdout) != 0) {
        status = 1;
    }
    if (checkpoint_out != NULL && es_checkpoint(&processor, checkpoint_out, stdout, fail_step) != 0) {
        status = 1;
    }
    uint64_t elapsed = monotonic_ns() - started;
    fprintf(stderr,
            "{\"implementation\":\"%s\",\"bytes\":%zu,\"accepted\":%" PRIu64
            ",\"rejected\":%" PRIu64 ",\"elapsed_ns\":%" PRIu64 "}\n",
            es_implementation_name(), bytes, processor.accepted, processor.rejected, elapsed);

    free(buffer);
    fclose(input);
    return status;
}
