package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReadableCheckpointRecoveryMatchesUninterrupted(t *testing.T) {
	values := []uint32{12, 30, 7, 9}
	uninterrupted, err := execute(context.Background(), config{rollback: true}, values)
	if err != nil {
		t.Fatal(err)
	}
	checkpointPath := filepath.Join(t.TempDir(), "state.json")
	_, err = execute(context.Background(), config{
		rollback:       true,
		checkpointPath: checkpointPath,
		failAfter:      2,
	}, values)
	if err == nil {
		t.Fatal("expected injected failure")
	}
	recovered, err := execute(context.Background(), config{
		rollback:       true,
		checkpointPath: checkpointPath,
		resume:         true,
	}, values)
	if err != nil {
		t.Fatal(err)
	}
	if recovered.Output != uninterrupted.Output || recovered.Checkpoint.Sum != uninterrupted.Checkpoint.Sum {
		t.Fatal("recovery diverged from uninterrupted execution")
	}
	if !recovered.Recovered {
		t.Fatal("recovery was not recorded")
	}
}

func TestCheckpointRejectsStaleInput(t *testing.T) {
	values := []uint32{1, 2, 3}
	checkpointPath := filepath.Join(t.TempDir(), "state.json")
	_, _ = execute(context.Background(), config{rollback: true, checkpointPath: checkpointPath, failAfter: 1}, values)
	_, err := execute(context.Background(), config{rollback: true, checkpointPath: checkpointPath, resume: true}, []uint32{1, 2, 4})
	if err == nil || !strings.Contains(err.Error(), "stale checkpoint") {
		t.Fatalf("expected stale checkpoint rejection, got %v", err)
	}
}

func TestCheckpointRejectsBindingIdentity(t *testing.T) {
	values := []uint32{1, 2}
	value := newCheckpoint(values, readableAuthority)
	value.BindingHeader = strings.Repeat("0", 64)
	value.StateDigest = checkpointDigest(value)
	if err := validateCheckpoint(value, values, readableAuthority, false); err == nil {
		t.Fatal("binding mismatch accepted")
	}
}

func TestCheckpointRejectsPartialState(t *testing.T) {
	values := []uint32{1, 2}
	value := newCheckpoint(values, readableAuthority)
	value.Processed = 1
	value.Sum = 2
	value.StateDigest = checkpointDigest(value)
	if err := validateCheckpoint(value, values, readableAuthority, false); err == nil {
		t.Fatal("semantically invalid partial state accepted")
	}
}

func TestControlledAuthorityReplacement(t *testing.T) {
	values := []uint32{5, 6}
	value := newCheckpoint(values, rustAuthority)
	value.Processed = 1
	value.Sum = 5
	value.StateDigest = checkpointDigest(value)
	checkpointPath := filepath.Join(t.TempDir(), "state.json")
	if err := writeCheckpoint(checkpointPath, value); err != nil {
		t.Fatal(err)
	}
	record, err := execute(context.Background(), config{
		rollback:       true,
		resume:         true,
		allowReplace:   true,
		checkpointPath: checkpointPath,
	}, values)
	if err != nil {
		t.Fatal(err)
	}
	if !record.Replaced || record.Checkpoint.Authority != readableAuthority || record.Checkpoint.Sum != 11 {
		t.Fatal("controlled replacement did not complete")
	}
}

func TestCheckpointTrailingDataRejected(t *testing.T) {
	values := []uint32{1}
	value := newCheckpoint(values, readableAuthority)
	encoded, _ := json.Marshal(value)
	path := filepath.Join(t.TempDir(), "state.json")
	encoded = append(encoded, []byte(` {"second":true}`)...)
	if err := os.WriteFile(path, encoded, 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := readCheckpoint(path); err == nil {
		t.Fatal("trailing checkpoint data accepted")
	}
}

func TestUnknownCheckpointFieldRejected(t *testing.T) {
	values := []uint32{1}
	value := newCheckpoint(values, readableAuthority)
	encoded, _ := json.Marshal(value)
	path := filepath.Join(t.TempDir(), "state.json")
	encoded = append(encoded[:len(encoded)-1], []byte(`,"unexpected":true}`)...)
	if err := os.WriteFile(path, encoded, 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := readCheckpoint(path); err == nil {
		t.Fatal("unknown checkpoint field accepted")
	}
}

func TestMalformedFramesAndLimits(t *testing.T) {
	for _, input := range []string{"x\n", "100001\n", "\n"} {
		if _, err := parseValues(strings.NewReader(input)); err == nil {
			t.Fatalf("accepted malformed input %q", input)
		}
	}
	var builder strings.Builder
	for i := 0; i < maxMessages+1; i++ {
		builder.WriteString("1\n")
	}
	if _, err := parseValues(strings.NewReader(builder.String())); err == nil {
		t.Fatal("accepted resource exhaustion")
	}
}

func FuzzParseNative(f *testing.F) {
	for _, seed := range []string{"0", "12", "100000", "x", "100001", ""} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, source string) {
		value, code := parseNative([]byte(source))
		if code == 0 && value > 100000 {
			t.Fatalf("accepted out-of-range value %d", value)
		}
	})
}

func BenchmarkNativeParse(b *testing.B) {
	input := []byte("12345")
	b.ReportAllocs()
	for index := 0; index < b.N; index++ {
		value, code := parseNative(input)
		if code != 0 || value != 12345 {
			b.Fatal("native parse mismatch")
		}
	}
}

func BenchmarkCheckpointDigest(b *testing.B) {
	value := newCheckpoint([]uint32{1, 2, 3, 4}, readableAuthority)
	b.ReportAllocs()
	for index := 0; index < b.N; index++ {
		if checkpointDigest(value) == "" {
			b.Fatal("empty digest")
		}
	}
}
