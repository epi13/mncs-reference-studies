package main

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type checkpoint struct {
	Version   int    `json:"version"`
	Binding   string `json:"binding"`
	Processed int    `json:"processed"`
	Sum       uint64 `json:"sum"`
}

func runAuthority(ctx context.Context, path string, items []uint32) (uint64, error) {
	command := exec.CommandContext(ctx, path)
	input, err := command.StdinPipe()
	if err != nil { return 0, err }
	output, err := command.StdoutPipe()
	if err != nil { return 0, err }
	if err = command.Start(); err != nil { return 0, err }
	scanner := bufio.NewScanner(output)
	var sum uint64
	for index, value := range items {
		if _, err = fmt.Fprintf(input, "V1 r%d %d\n", index, value); err != nil { return 0, err }
		if !scanner.Scan() { return 0, errors.New("partial response") }
		parts := strings.Fields(scanner.Text())
		if len(parts) != 3 || parts[0] != "OK" { return 0, errors.New("authority rejected") }
		parsed, _ := strconv.ParseUint(parts[2], 10, 32)
		sum += parsed
	}
	input.Close()
	if err = command.Wait(); err != nil { return 0, err }
	return sum, nil
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	rollback := os.Getenv("MNCS_ROLLBACK") == "1"
	scanner := bufio.NewScanner(os.Stdin)
	values := []uint32{}
	for scanner.Scan() {
		value, code := parseNative(scanner.Bytes())
		if code != 0 { fmt.Fprintln(os.Stderr, "invalid frame"); os.Exit(2) }
		values = append(values, value)
		if len(values) > 64 { fmt.Fprintln(os.Stderr, "resource limit"); os.Exit(2) }
	}
	var sum uint64
	var err error
	if rollback {
		for _, value := range values { sum += uint64(value) }
	} else {
		sum, err = runAuthority(ctx, os.Getenv("MNCS_RUST_AUTHORITY"), values)
	}
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(3) }
	record := checkpoint{1, BindingHeaderSHA256, len(values), sum}
	encoded, _ := json.Marshal(record)
	fmt.Println(string(encoded))
}
