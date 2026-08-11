package service

import (
	"bytes"
	"context"
	"net/http"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestLoopbackContract(t *testing.T) {
	server, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	defer server.Close(context.Background())
	response, err := Evaluate(context.Background(), server.URL(), Request{Version: "V1", ID: "r1", Value: 42})
	if err != nil || response.Value != 42 {
		t.Fatalf("unexpected response: %#v %v", response, err)
	}
}

func TestMalformedAndVersionMismatch(t *testing.T) {
	server, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	defer server.Close(context.Background())
	cases := []string{
		`{"version":"V2","id":"r1","value":1}`,
		`{"version":"V1","id":"","value":1}`,
		`{"version":"V1","id":"r1","value":100001}`,
		`{"version":"V1","id":"r1","value":1,"extra":true}`,
		`not-json`,
	}
	for _, body := range cases {
		request, _ := http.NewRequest(http.MethodPost, server.URL()+"/v1/evaluate", strings.NewReader(body))
		request.Header.Set("Content-Type", "application/json")
		response, err := http.DefaultClient.Do(request)
		if err != nil {
			t.Fatal(err)
		}
		response.Body.Close()
		if response.StatusCode == http.StatusOK {
			t.Fatalf("accepted malformed body %q", body)
		}
	}
}

func TestResourceLimitAndMethod(t *testing.T) {
	server, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	defer server.Close(context.Background())
	request, _ := http.NewRequest(http.MethodPost, server.URL()+"/v1/evaluate", bytes.NewReader(make([]byte, MaxBodyBytes+1)))
	request.Header.Set("Content-Type", "application/json")
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	response.Body.Close()
	if response.StatusCode == http.StatusOK {
		t.Fatal("oversized body accepted")
	}
	getResponse, err := http.Get(server.URL() + "/v1/evaluate")
	if err != nil {
		t.Fatal(err)
	}
	getResponse.Body.Close()
	if getResponse.StatusCode == http.StatusOK {
		t.Fatal("GET accepted")
	}
}

func TestCancellationAndShutdown(t *testing.T) {
	before := runtime.NumGoroutine()
	server, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := Evaluate(ctx, server.URL(), Request{Version: "V1", ID: "r1", Value: 1}); err == nil {
		t.Fatal("cancelled request succeeded")
	}
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), time.Second)
	defer shutdownCancel()
	if err := server.Close(shutdownCtx); err != nil {
		t.Fatal(err)
	}
	time.Sleep(20 * time.Millisecond)
	if runtime.NumGoroutine() > before+4 {
		t.Fatal("bounded shutdown goroutine observation failed")
	}
}

func TestServiceManagerStyleRestart(t *testing.T) {
	first, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Evaluate(context.Background(), first.URL(), Request{Version: "V1", ID: "before", Value: 7}); err != nil {
		t.Fatal(err)
	}
	shutdownCtx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	if err := first.Close(shutdownCtx); err != nil {
		t.Fatal(err)
	}
	second, err := StartLoopback()
	if err != nil {
		t.Fatal(err)
	}
	defer second.Close(context.Background())
	response, err := Evaluate(context.Background(), second.URL(), Request{Version: "V1", ID: "after", Value: 7})
	if err != nil || response.ID != "after" {
		t.Fatalf("restart failed: %#v %v", response, err)
	}
}
