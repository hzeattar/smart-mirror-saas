<?php

return [
    'enabled' => (bool) env('LIVE_RESTYLE_ENABLED', false),
    'provider' => env('LIVE_RESTYLE_PROVIDER', 'fal'),
    'model' => env('LIVE_RESTYLE_MODEL', 'decart/lucy2-vton/realtime'),
    'max_seconds' => (int) env('LIVE_RESTYLE_MAX_SECONDS', 20),
    'daily_seconds_limit' => env('LIVE_RESTYLE_DAILY_SECONDS_LIMIT') !== null
        ? (int) env('LIVE_RESTYLE_DAILY_SECONDS_LIMIT')
        : 120,
    'price_per_second_usd' => (float) env('LIVE_RESTYLE_PRICE_PER_SECOND_USD', 0.02),
    'local_proxy_url' => env('LIVE_RESTYLE_LOCAL_PROXY_URL', 'http://127.0.0.1:8787'),
];
