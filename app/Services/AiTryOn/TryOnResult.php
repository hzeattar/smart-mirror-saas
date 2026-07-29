<?php

namespace App\Services\AiTryOn;

class TryOnResult
{
    public function __construct(
        public readonly string $bytes,
        public readonly string $extension = 'jpg',
        public readonly string $mimeType = 'image/jpeg',
    ) {}
}
