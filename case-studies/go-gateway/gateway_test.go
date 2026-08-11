package gateway

import (
	"context"
	"runtime"
	"testing"
	"time"
)

func TestBaselineCandidateComplete(t *testing.T) {
	input, _ := ParseTrace("a,3,2\nb,4,1\nc,5,0")
	baseline, err := (Gateway{2, BaselinePolicy{}}).Run(context.Background(), input)
	if err != nil {
		t.Fatal(err)
	}
	candidate, err := (Gateway{2, GeneratedPolicy{}}).Run(context.Background(), input)
	if err != nil || len(baseline) != len(candidate) {
		t.Fatal("candidate did not preserve completion")
	}
}

func TestMalformed(t *testing.T) {
	for _, source := range []string{"x", "a,-1,0", "a,1,0\na,2,0", "a,1,1001"} {
		if _, err := ParseTrace(source); err == nil {
			t.Fatalf("accepted %q", source)
		}
	}
}

func TestCancellationAndLeakBound(t *testing.T) {
	before := runtime.NumGoroutine()
	input, _ := ParseTrace("a,3,100\nb,4,100")
	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond)
	defer cancel()
	if _, err := (Gateway{2, GeneratedPolicy{}}).Run(ctx, input); err == nil {
		t.Fatal("expected cancellation")
	}
	time.Sleep(10 * time.Millisecond)
	if runtime.NumGoroutine() > before+2 {
		t.Fatal("goroutine leak")
	}
}

func FuzzParse(f *testing.F) {
	f.Add("a,1,0")
	f.Fuzz(func(t *testing.T, source string) { _, _ = ParseTrace(source) })
}
