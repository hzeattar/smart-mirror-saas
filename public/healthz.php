<?php

declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate');

$ready = is_file('/tmp/smart-mirror-ready');
http_response_code($ready ? 200 : 503);

echo json_encode([
    'status' => $ready ? 'ok' : 'starting',
    'service' => 'smart-mirror-saas',
    'timestamp' => gmdate(DATE_ATOM),
], JSON_UNESCAPED_SLASHES);
