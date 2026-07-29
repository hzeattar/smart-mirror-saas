<?php

return [
    'provider' => env('AI_TRYON_PROVIDER', 'mock'),
    'retention_hours' => (int) env('AI_TRYON_RETENTION_HOURS', 24),
    'timeout_seconds' => (int) env('AI_TRYON_TIMEOUT_SECONDS', 120),
    'nvidia' => [
        'api_key' => env('NVIDIA_API_KEY'),
        'base_url' => env('NVIDIA_API_BASE', 'https://integrate.api.nvidia.com/v1'),
        'model' => env('NVIDIA_TRYON_MODEL'),
    ],
];
