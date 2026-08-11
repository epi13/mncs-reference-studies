package gateway

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"
)

const MaxQueue = 32

type Request struct {
	ID    string
	Value int
	Delay time.Duration
}
type Result struct {
	ID    string
	Value int
}
type Policy interface{ Order([]Request) []Request }
type BaselinePolicy struct{}

func (BaselinePolicy) Order(in []Request) []Request { return append([]Request(nil), in...) }

type GeneratedPolicy struct{}

func (GeneratedPolicy) Order(in []Request) []Request {
	out := append([]Request(nil), in...)
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j].Delay < out[j-1].Delay; j-- {
			out[j], out[j-1] = out[j-1], out[j]
		}
	}
	return out
}

type Gateway struct {
	Workers int
	Policy  Policy
}

func ParseTrace(text string) ([]Request, error) {
	lines := strings.Split(strings.TrimSpace(text), "\n")
	if len(lines) == 1 && lines[0] == "" {
		return nil, nil
	}
	if len(lines) > MaxQueue {
		return nil, errors.New("queue limit")
	}
	seen := map[string]bool{}
	out := make([]Request, 0, len(lines))
	for _, line := range lines {
		parts := strings.Split(line, ",")
		if len(parts) != 3 || parts[0] == "" || seen[parts[0]] {
			return nil, errors.New("malformed or duplicate id")
		}
		seen[parts[0]] = true
		value, err := strconv.Atoi(parts[1])
		if err != nil || value < 0 || value > 100000 {
			return nil, errors.New("invalid value")
		}
		milliseconds, err := strconv.Atoi(parts[2])
		if err != nil || milliseconds < 0 || milliseconds > 1000 {
			return nil, errors.New("invalid delay")
		}
		out = append(out, Request{parts[0], value, time.Duration(milliseconds) * time.Millisecond})
	}
	return out, nil
}

func (g Gateway) Run(ctx context.Context, in []Request) ([]Result, error) {
	if g.Workers < 1 || g.Workers > 8 || len(in) > MaxQueue {
		return nil, errors.New("resource bound")
	}
	jobs := make(chan Request)
	results := make(chan Result, len(in))
	var workers sync.WaitGroup
	worker := func() {
		defer workers.Done()
		for {
			select {
			case <-ctx.Done():
				return
			case request, ok := <-jobs:
				if !ok {
					return
				}
				select {
				case <-ctx.Done():
					return
				case <-time.After(request.Delay):
				}
				select {
				case results <- Result{request.ID, request.Value * request.Value}:
				case <-ctx.Done():
					return
				}
			}
		}
	}
	for index := 0; index < g.Workers; index++ {
		workers.Add(1)
		go worker()
	}
	go func() {
		defer close(jobs)
		for _, request := range g.Policy.Order(in) {
			select {
			case jobs <- request:
			case <-ctx.Done():
				return
			}
		}
	}()
	go func() { workers.Wait(); close(results) }()
	out := make([]Result, 0, len(in))
	for result := range results {
		out = append(out, result)
	}
	if ctx.Err() != nil {
		return nil, ctx.Err()
	}
	if len(out) != len(in) {
		return nil, errors.New("incomplete")
	}
	return out, nil
}

func Digest(results []Result) string {
	hash := sha256.New()
	for _, result := range results {
		fmt.Fprintf(hash, "%s:%d\n", result.ID, result.Value)
	}
	return hex.EncodeToString(hash.Sum(nil))
}
