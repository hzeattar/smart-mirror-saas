<?php

namespace App\Services\AiTryOn;

use RuntimeException;

class AiTryOnProviderFactory
{
    public function make(?string $provider = null): AiTryOnProvider
    {
        return match ($provider ?: config('ai_tryon.provider', 'mock')) {
            'mock' => app(MockTryOnProvider::class),
            'nvidia' => app(NvidiaTryOnProvider::class),
            'local_vton' => app(LocalVtonProvider::class),
            default => throw new RuntimeException('Unsupported AI try-on provider.'),
        };
    }
}
