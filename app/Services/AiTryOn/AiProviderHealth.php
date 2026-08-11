<?php

namespace App\Services\AiTryOn;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Cache;

class AiProviderHealth
{
    private const CACHE_KEY = 'ai-tryon:provider-health';

    public function snapshot(): array
    {
        $provider = (string) config('ai_tryon.provider', 'mock');
        if ($provider !== 'nvidia') {
            return [
                'provider' => $provider,
                'available' => $provider === 'mock',
                'status' => $provider === 'mock' ? 'mock' : 'disabled',
                'checked_at' => now()->toIso8601String(),
                'error' => null,
            ];
        }

        $health = Cache::get(self::CACHE_KEY);
        if (! is_array($health)) {
            return $this->unknown($provider, 'Provider health has not been checked yet.');
        }

        $checkedAt = isset($health['checked_at']) ? CarbonImmutable::parse($health['checked_at']) : null;
        if (! $checkedAt || $checkedAt->lt(now()->subMinutes(3))) {
            return $this->unknown($provider, 'Provider health check is stale.');
        }

        return [
            'provider' => $provider,
            'available' => (bool) ($health['available'] ?? false),
            'status' => (string) ($health['status'] ?? 'unavailable'),
            'checked_at' => $checkedAt->toIso8601String(),
            'error' => $health['error'] ?? null,
        ];
    }

    public function record(bool $available, string $status, ?string $error = null): array
    {
        $health = [
            'provider' => (string) config('ai_tryon.provider', 'mock'),
            'available' => $available,
            'status' => $status,
            'checked_at' => now()->toIso8601String(),
            'error' => $error ? str($error)->limit(300)->toString() : null,
        ];
        Cache::put(self::CACHE_KEY, $health, now()->addMinutes(5));

        return $health;
    }

    private function unknown(string $provider, string $error): array
    {
        return [
            'provider' => $provider,
            'available' => false,
            'status' => 'unknown',
            'checked_at' => null,
            'error' => $error,
        ];
    }
}
