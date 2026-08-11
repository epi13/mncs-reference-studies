package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"sync"
	"time"
)

const MaxBodyBytes int64 = 1024

type Request struct {
	Version string `json:"version"`
	ID      string `json:"id"`
	Value   uint32 `json:"value"`
}

type Response struct {
	Version  string `json:"version"`
	ID       string `json:"id"`
	Decision string `json:"decision"`
	Value    uint32 `json:"value"`
}

type Server struct {
	server   *http.Server
	listener net.Listener
	once     sync.Once
}

func handler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost || r.URL.Path != "/v1/evaluate" {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	if r.Header.Get("Content-Type") != "application/json" {
		http.Error(w, "content type", http.StatusUnsupportedMediaType)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, MaxBodyBytes)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var request Request
	if err := decoder.Decode(&request); err != nil {
		http.Error(w, "malformed", http.StatusBadRequest)
		return
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		http.Error(w, "trailing data", http.StatusBadRequest)
		return
	}
	if request.Version != "V1" || request.ID == "" || request.Value > 100000 {
		http.Error(w, "contract", http.StatusUnprocessableEntity)
		return
	}
	select {
	case <-r.Context().Done():
		return
	default:
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(Response{Version: "V1", ID: request.ID, Decision: "ACCEPT", Value: request.Value})
}

func StartLoopback() (*Server, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, err
	}
	server := &http.Server{
		Handler:           http.HandlerFunc(handler),
		ReadHeaderTimeout: time.Second,
		ReadTimeout:       time.Second,
		WriteTimeout:      time.Second,
		IdleTimeout:       time.Second,
	}
	result := &Server{server: server, listener: listener}
	go func() { _ = server.Serve(listener) }()
	return result, nil
}

func (s *Server) URL() string { return "http://" + s.listener.Addr().String() }

func (s *Server) Close(ctx context.Context) error {
	var result error
	s.once.Do(func() { result = s.server.Shutdown(ctx) })
	return result
}

func Evaluate(ctx context.Context, baseURL string, request Request) (Response, error) {
	body, err := json.Marshal(request)
	if err != nil {
		return Response{}, err
	}
	httpRequest, err := http.NewRequestWithContext(ctx, http.MethodPost, baseURL+"/v1/evaluate", bytesReader(body))
	if err != nil {
		return Response{}, err
	}
	httpRequest.Header.Set("Content-Type", "application/json")
	response, err := http.DefaultClient.Do(httpRequest)
	if err != nil {
		return Response{}, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return Response{}, fmt.Errorf("service status %d", response.StatusCode)
	}
	var decoded Response
	decoder := json.NewDecoder(io.LimitReader(response.Body, MaxBodyBytes))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&decoded); err != nil {
		return Response{}, err
	}
	if decoded.Version != "V1" || decoded.ID != request.ID || decoded.Value != request.Value || decoded.Decision != "ACCEPT" {
		return Response{}, errors.New("response contract mismatch")
	}
	return decoded, nil
}

type byteReader struct {
	data   []byte
	offset int
}

func bytesReader(data []byte) *byteReader { return &byteReader{data: data} }

func (r *byteReader) Read(p []byte) (int, error) {
	if r.offset >= len(r.data) {
		return 0, io.EOF
	}
	n := copy(p, r.data[r.offset:])
	r.offset += n
	return n, nil
}
