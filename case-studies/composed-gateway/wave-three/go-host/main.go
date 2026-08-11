package main

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	checkpointVersion = 2
	systemContractID  = "contract:composed-gateway-wave3-0.2"
	readableAuthority = "go-readable-authority-v2"
	rustAuthority     = "rust-authority-v2"
	maxMessages       = 64
	maxLineBytes      = 128
)

type checkpoint struct {
	Version          int    `json:"version"`
	SystemContract   string `json:"system_contract"`
	BindingHeader    string `json:"binding_header"`
	BindingSpec      string `json:"binding_spec"`
	BindingGenerator string `json:"binding_generator"`
	Authority        string `json:"authority"`
	InputDigest      string `json:"input_digest"`
	Processed        int    `json:"processed"`
	Sum              uint64 `json:"sum"`
	StateDigest      string `json:"state_digest"`
}

type finalRecord struct {
	Checkpoint checkpoint `json:"checkpoint"`
	Mode       string     `json:"mode"`
	Output     string     `json:"output_digest"`
	Recovered  bool       `json:"recovered"`
	Replaced   bool       `json:"replaced"`
}

type config struct {
	authorityPath  string
	checkpointPath string
	resume         bool
	rollback       bool
	fallback       bool
	allowReplace   bool
	failAfter      int
	timeout        time.Duration
}

func checkpointDigest(value checkpoint) string {
	hash := sha256.New()
	fmt.Fprintf(
		hash,
		"%d\n%s\n%s\n%s\n%s\n%s\n%s\n%d\n%d\n",
		value.Version,
		value.SystemContract,
		value.BindingHeader,
		value.BindingSpec,
		value.BindingGenerator,
		value.Authority,
		value.InputDigest,
		value.Processed,
		value.Sum,
	)
	return hex.EncodeToString(hash.Sum(nil))
}

func outputDigest(inputDigest string, processed int, sum uint64) string {
	value := sha256.Sum256([]byte(fmt.Sprintf("%s\n%d\n%d\n", inputDigest, processed, sum)))
	return hex.EncodeToString(value[:])
}

func inputDigest(values []uint32) string {
	hash := sha256.New()
	for _, value := range values {
		fmt.Fprintf(hash, "%d\n", value)
	}
	return hex.EncodeToString(hash.Sum(nil))
}

func newCheckpoint(values []uint32, authority string) checkpoint {
	value := checkpoint{
		Version:          checkpointVersion,
		SystemContract:   systemContractID,
		BindingHeader:    BindingHeaderSHA256,
		BindingSpec:      BindingSpecSHA256,
		BindingGenerator: BindingGeneratorID,
		Authority:        authority,
		InputDigest:      inputDigest(values),
	}
	value.StateDigest = checkpointDigest(value)
	return value
}

func validateCheckpoint(value checkpoint, values []uint32, authority string, allowReplace bool) error {
	if value.Version != checkpointVersion || value.SystemContract != systemContractID {
		return errors.New("checkpoint contract mismatch")
	}
	if value.BindingHeader != BindingHeaderSHA256 || value.BindingSpec != BindingSpecSHA256 || value.BindingGenerator != BindingGeneratorID {
		return errors.New("checkpoint binding identity mismatch")
	}
	if value.InputDigest != inputDigest(values) {
		return errors.New("stale checkpoint input identity")
	}
	if value.Processed < 0 || value.Processed > len(values) {
		return errors.New("checkpoint processed range")
	}
	if value.StateDigest != checkpointDigest(value) {
		return errors.New("checkpoint state digest mismatch")
	}
	var expectedSum uint64
	for _, item := range values[:value.Processed] {
		expectedSum += uint64(item)
	}
	if value.Sum != expectedSum {
		return errors.New("checkpoint partial state mismatch")
	}
	if value.Authority != authority {
		if !(allowReplace && value.Authority == rustAuthority && authority == readableAuthority) {
			return errors.New("checkpoint authority identity mismatch")
		}
	}
	return nil
}

func writeCheckpoint(path string, value checkpoint) error {
	if path == "" {
		return nil
	}
	value.StateDigest = checkpointDigest(value)
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	temporary := path + ".tmp"
	if err := os.WriteFile(temporary, append(encoded, '\n'), 0o600); err != nil {
		return err
	}
	return os.Rename(temporary, path)
}

func readCheckpoint(path string) (checkpoint, error) {
	var value checkpoint
	encoded, err := os.ReadFile(path)
	if err != nil {
		return value, err
	}
	decoder := json.NewDecoder(strings.NewReader(string(encoded)))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&value); err != nil {
		return value, err
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		return value, errors.New("checkpoint trailing data")
	}
	return value, nil
}

func parseValues(reader io.Reader) ([]uint32, error) {
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 1024), maxLineBytes)
	values := make([]uint32, 0, 16)
	for scanner.Scan() {
		value, code := parseNative(scanner.Bytes())
		if code != 0 {
			return nil, fmt.Errorf("invalid frame: code %d", code)
		}
		values = append(values, value)
		if len(values) > maxMessages {
			return nil, errors.New("resource limit")
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return values, nil
}

func applyValue(value *checkpoint, item uint32, path string, failAfter int) error {
	value.Sum += uint64(item)
	value.Processed++
	value.StateDigest = checkpointDigest(*value)
	if err := writeCheckpoint(path, *value); err != nil {
		return err
	}
	if failAfter > 0 && value.Processed == failAfter {
		return errors.New("injected component failure")
	}
	return nil
}

func processReadable(value *checkpoint, values []uint32, path string, failAfter int) error {
	for index := value.Processed; index < len(values); index++ {
		if err := applyValue(value, values[index], path, failAfter); err != nil {
			return err
		}
	}
	return nil
}

func runAuthority(ctx context.Context, path string, value *checkpoint, values []uint32, checkpointPath string, failAfter int) error {
	if path == "" {
		return errors.New("authority path missing")
	}
	command := exec.CommandContext(ctx, path)
	input, err := command.StdinPipe()
	if err != nil {
		return err
	}
	output, err := command.StdoutPipe()
	if err != nil {
		return err
	}
	if err := command.Start(); err != nil {
		return err
	}
	abort := func() {
		if command.Process != nil {
			_ = command.Process.Kill()
		}
		_ = command.Wait()
	}
	scanner := bufio.NewScanner(output)
	scanner.Buffer(make([]byte, 1024), maxLineBytes)
	if !scanner.Scan() {
		abort()
		if err := scanner.Err(); err != nil {
			return fmt.Errorf("authority handshake: %w", err)
		}
		return errors.New("authority handshake missing")
	}
	if scanner.Text() != "READY V2 "+rustAuthority {
		abort()
		return errors.New("authority identity or protocol mismatch")
	}
	for index := value.Processed; index < len(values); index++ {
		requestID := fmt.Sprintf("r%d", index)
		if _, err := fmt.Fprintf(input, "V2 %s %d\n", requestID, values[index]); err != nil {
			abort()
			return err
		}
		if !scanner.Scan() {
			abort()
			if err := scanner.Err(); err != nil {
				return fmt.Errorf("authority response: %w", err)
			}
			return errors.New("partial authority response")
		}
		parts := strings.Fields(scanner.Text())
		if len(parts) != 3 || parts[0] != "OK" || parts[1] != requestID {
			abort()
			return errors.New("authority rejected or misordered response")
		}
		parsed, err := strconv.ParseUint(parts[2], 10, 32)
		if err != nil || uint32(parsed) != values[index] {
			abort()
			return errors.New("authority value mismatch")
		}
		if err := applyValue(value, uint32(parsed), checkpointPath, failAfter); err != nil {
			abort()
			return err
		}
	}
	if err := input.Close(); err != nil {
		abort()
		return err
	}
	if err := command.Wait(); err != nil {
		return err
	}
	return nil
}

func execute(ctx context.Context, cfg config, values []uint32) (finalRecord, error) {
	authority := rustAuthority
	mode := "composed"
	if cfg.rollback {
		authority = readableAuthority
		mode = "readable-rollback"
	}
	state := newCheckpoint(values, authority)
	recovered := false
	replaced := false
	if cfg.resume {
		loaded, err := readCheckpoint(cfg.checkpointPath)
		if err != nil {
			return finalRecord{}, err
		}
		if err := validateCheckpoint(loaded, values, authority, cfg.allowReplace); err != nil {
			return finalRecord{}, err
		}
		state = loaded
		recovered = true
		if state.Authority != authority {
			state.Authority = authority
			state.StateDigest = checkpointDigest(state)
			replaced = true
			if err := writeCheckpoint(cfg.checkpointPath, state); err != nil {
				return finalRecord{}, err
			}
		}
	}

	var err error
	if authority == readableAuthority {
		err = processReadable(&state, values, cfg.checkpointPath, cfg.failAfter)
	} else {
		err = runAuthority(ctx, cfg.authorityPath, &state, values, cfg.checkpointPath, cfg.failAfter)
	}
	if err != nil && cfg.fallback && cfg.allowReplace && state.Processed < len(values) {
		state.Authority = readableAuthority
		state.StateDigest = checkpointDigest(state)
		if writeErr := writeCheckpoint(cfg.checkpointPath, state); writeErr != nil {
			return finalRecord{}, writeErr
		}
		replaced = true
		mode = "readable-replacement"
		err = processReadable(&state, values, cfg.checkpointPath, 0)
	}
	if err != nil {
		return finalRecord{}, err
	}
	if state.Processed != len(values) {
		return finalRecord{}, errors.New("incomplete execution")
	}
	state.StateDigest = checkpointDigest(state)
	if err := writeCheckpoint(cfg.checkpointPath, state); err != nil {
		return finalRecord{}, err
	}
	return finalRecord{
		Checkpoint: state,
		Mode:       mode,
		Output:     outputDigest(state.InputDigest, state.Processed, state.Sum),
		Recovered:  recovered,
		Replaced:   replaced,
	}, nil
}

func configFromEnvironment() (config, error) {
	failAfter := 0
	if raw := os.Getenv("MNCS_FAIL_AFTER"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil || parsed < 1 || parsed > maxMessages {
			return config{}, errors.New("invalid MNCS_FAIL_AFTER")
		}
		failAfter = parsed
	}
	timeout := 2 * time.Second
	if raw := os.Getenv("MNCS_TIMEOUT_MS"); raw != "" {
		milliseconds, err := strconv.Atoi(raw)
		if err != nil || milliseconds < 1 || milliseconds > 10000 {
			return config{}, errors.New("invalid MNCS_TIMEOUT_MS")
		}
		timeout = time.Duration(milliseconds) * time.Millisecond
	}
	return config{
		authorityPath:  os.Getenv("MNCS_RUST_AUTHORITY"),
		checkpointPath: os.Getenv("MNCS_CHECKPOINT_PATH"),
		resume:         os.Getenv("MNCS_RESUME") == "1",
		rollback:       os.Getenv("MNCS_ROLLBACK") == "1",
		fallback:       os.Getenv("MNCS_FALLBACK") == "1",
		allowReplace:   os.Getenv("MNCS_ALLOW_READABLE_REPLACEMENT") == "1",
		failAfter:      failAfter,
		timeout:        timeout,
	}, nil
}

func main() {
	cfg, err := configFromEnvironment()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	values, err := parseValues(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	ctx, cancel := context.WithTimeout(context.Background(), cfg.timeout)
	defer cancel()
	record, err := execute(ctx, cfg, values)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(3)
	}
	encoded, err := json.Marshal(record)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(70)
	}
	fmt.Println(string(encoded))
}
