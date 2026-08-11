<?php

return [
    'enabled' => (bool) env('RUNPOD_ENABLED', false),
    'api_base' => env('RUNPOD_API_BASE', 'https://rest.runpod.io/v1'),
    'api_key' => env('RUNPOD_API_KEY'),
    'pod_id' => env('RUNPOD_POD_ID'),
    'timezone' => env('RUNPOD_TIMEZONE', 'Africa/Cairo'),
    'active_start' => env('RUNPOD_ACTIVE_START', '09:30'),
    'active_end' => env('RUNPOD_ACTIVE_END', '22:15'),
];
