package main

import (
	"crypto/subtle"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
)

const defaultMaxBodyMB = 50

type gateway struct {
	token        string
	maxBodyBytes int64
	proxy        *httputil.ReverseProxy
	slots        chan struct{}
}

func main() {
	token := strings.TrimSpace(os.Getenv("GATEWAY_BEARER_TOKEN"))
	if token == "" {
		log.Fatal("GATEWAY_BEARER_TOKEN is required")
	}
	upstream, err := url.Parse(envOr("NIM_UPSTREAM_URL", "http://127.0.0.1:8000"))
	if err != nil {
		log.Fatalf("invalid NIM_UPSTREAM_URL: %v", err)
	}
	maxBodyBytes := int64(envInt("GATEWAY_MAX_BODY_MB", defaultMaxBodyMB)) * 1024 * 1024
	concurrency := envInt("GATEWAY_MAX_CONCURRENCY", 2)
	proxy := httputil.NewSingleHostReverseProxy(upstream)
	proxy.Transport = &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          8,
		MaxIdleConnsPerHost:   4,
		IdleConnTimeout:       30 * time.Second,
		ResponseHeaderTimeout: 90 * time.Second,
	}
	baseDirector := proxy.Director
	proxy.Director = func(request *http.Request) {
		baseDirector(request)
		request.Header.Del("Authorization")
		request.Header.Set("X-Forwarded-Proto", "https")
	}
	proxy.ErrorHandler = func(writer http.ResponseWriter, _ *http.Request, proxyErr error) {
		log.Printf("upstream error: %v", proxyErr)
		http.Error(writer, "NVIDIA NIM is temporarily unavailable", http.StatusBadGateway)
	}

	handler := &gateway{
		token:        token,
		maxBodyBytes: maxBodyBytes,
		proxy:        proxy,
		slots:        make(chan struct{}, max(1, concurrency)),
	}
	server := &http.Server{
		Addr:              ":" + envOr("PORT", "8080"),
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       20 * time.Second,
		WriteTimeout:      95 * time.Second,
		IdleTimeout:       30 * time.Second,
		MaxHeaderBytes:    32 * 1024,
	}
	log.Printf("NVIDIA NIM gateway listening on %s", server.Addr)
	log.Fatal(server.ListenAndServe())
}

func (gateway *gateway) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	writer.Header().Set("Cache-Control", "no-store")
	writer.Header().Set("X-Content-Type-Options", "nosniff")
	if request.URL.Path == "/healthz" && request.Method == http.MethodGet {
		writer.Header().Set("Content-Type", "application/json")
		writer.WriteHeader(http.StatusOK)
		_, _ = writer.Write([]byte(`{"status":"live"}`))
		return
	}
	if !gateway.authorized(request) {
		writer.Header().Set("WWW-Authenticate", "Bearer")
		http.Error(writer, "Unauthorized", http.StatusUnauthorized)
		return
	}
	if !allowedRoute(request) {
		http.NotFound(writer, request)
		return
	}
	if request.ContentLength > gateway.maxBodyBytes {
		http.Error(writer, "Request body too large", http.StatusRequestEntityTooLarge)
		return
	}
	request.Body = http.MaxBytesReader(writer, request.Body, gateway.maxBodyBytes)
	select {
	case gateway.slots <- struct{}{}:
		defer func() { <-gateway.slots }()
	default:
		http.Error(writer, "NVIDIA NIM is busy", http.StatusTooManyRequests)
		return
	}
	gateway.proxy.ServeHTTP(writer, request)
}

func (gateway *gateway) authorized(request *http.Request) bool {
	header := strings.TrimSpace(request.Header.Get("Authorization"))
	if len(header) < 7 || !strings.EqualFold(header[:7], "Bearer ") {
		return false
	}
	provided := strings.TrimSpace(header[7:])
	if provided == "" || len(provided) != len(gateway.token) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(provided), []byte(gateway.token)) == 1
}

func allowedRoute(request *http.Request) bool {
	if request.Method == http.MethodPost && request.URL.Path == "/v1/images/edits" {
		return true
	}
	return request.Method == http.MethodGet && request.URL.Path == "/v1/health/ready"
}

func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func envInt(key string, fallback int) int {
	value, err := strconv.Atoi(strings.TrimSpace(os.Getenv(key)))
	if err != nil || value <= 0 {
		return fallback
	}
	return value
}
