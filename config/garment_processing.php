<?php

return [
    'endpoint' => env('BACKGROUND_REMOVAL_URL'),
    'api_token' => env('BACKGROUND_REMOVAL_TOKEN'),
    'python_binary' => env('PYTHON_BINARY', 'python3'),
];
