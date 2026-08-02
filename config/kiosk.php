<?php

return [
    'experience_mode' => env('KIOSK_EXPERIENCE_MODE', 'hybrid'),
    'outfit_count' => (int) env('KIOSK_OUTFIT_COUNT', 3),
    'auto_start_delay_seconds' => (float) env('KIOSK_AUTO_START_DELAY_SECONDS', 1.5),
    'capture_burst_count' => (int) env('KIOSK_CAPTURE_BURST_COUNT', 5),
    'capture_duration_seconds' => (float) env('KIOSK_CAPTURE_DURATION_SECONDS', 2.0),
    'gallery_timeout_seconds' => (float) env('KIOSK_GALLERY_TIMEOUT_SECONDS', 45),
    'poll_interval_seconds' => (float) env('KIOSK_POLL_INTERVAL_SECONDS', 2.5),
    'pose_every_n' => (int) env('KIOSK_POSE_EVERY_N', 3),
    'hand_every_n' => (int) env('KIOSK_HAND_EVERY_N', 3),
    'kiosk_health_hud' => (bool) env('KIOSK_HEALTH_HUD', true),
    'gestures' => [
        'cooldown_seconds' => (float) env('KIOSK_GESTURE_COOLDOWN_SECONDS', 1.1),
        'hold_seconds' => (float) env('KIOSK_GESTURE_HOLD_SECONDS', 0.75),
        'swipe_distance' => (float) env('KIOSK_GESTURE_SWIPE_DISTANCE', 0.20),
    ],
];
