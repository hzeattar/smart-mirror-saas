<?php

return [
    'provider' => env('AI_TRYON_PROVIDER', 'mock'),
    'retention_hours' => (int) env('AI_TRYON_RETENTION_HOURS', 24),
    'timeout_seconds' => (int) env('AI_TRYON_TIMEOUT_SECONDS', 90),
    'nvidia' => [
        'api_key' => env('NVIDIA_API_KEY'),
        'endpoint' => env('NVIDIA_TRYON_ENDPOINT'),
        'health_endpoint' => env('NVIDIA_HEALTH_ENDPOINT'),
        'model' => env('NVIDIA_TRYON_MODEL', 'flux.2-klein-4b'),
        'prompt' => env('NVIDIA_TRYON_PROMPT'),
    ],
    'local_vton' => [
        'base_url' => env('LOCAL_VTON_BASE_URL', 'http://127.0.0.1:8788'),
        'model' => env('LOCAL_VTON_MODEL', 'idm-vton'),
    ],
];
