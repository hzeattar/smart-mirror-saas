package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAllowedRoutes(t *testing.T) {
	tests := []struct {
		method  string
		path    string
		allowed bool
	}{
		{http.MethodPost, "/v1/images/edits", true},
		{http.MethodGet, "/v1/health/ready", true},
		{http.MethodGet, "/v1/images/edits", false},
		{http.MethodGet, "/v1/metrics", false},
	}
	for _, test := range tests {
		request := httptest.NewRequest(test.method, test.path, nil)
		if allowedRoute(request) != test.allowed {
			t.Fatalf("route %s %s allowed=%v", test.method, test.path, !test.allowed)
		}
	}
}

func TestAuthorization(t *testing.T) {
	gateway := &gateway{token: "secret-token"}
	request := httptest.NewRequest(http.MethodGet, "/v1/health/ready", nil)
	request.Header.Set("Authorization", "Bearer secret-token")
	if !gateway.authorized(request) {
		t.Fatal("expected bearer token to be accepted")
	}
	request.Header.Set("Authorization", "Bearer wrong-token")
	if gateway.authorized(request) {
		t.Fatal("expected wrong bearer token to be rejected")
	}
	request.Header.Set("Authorization", "secret-token")
	if gateway.authorized(request) {
		t.Fatal("expected missing Bearer scheme to be rejected")
	}
}
