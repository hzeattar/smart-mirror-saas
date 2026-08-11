<?php

namespace App\Console\Commands;

use App\Services\AiTryOn\AiProviderHealth;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use Throwable;

class CheckAiProviderHealth extends Command
{
    protected $signature = 'ai:check-provider';

    protected $description = 'Check the configured AI try-on provider and publish kiosk availability.';

    public function handle(AiProviderHealth $health): int
    {
        $provider = (string) config('ai_tryon.provider', 'mock');
        if ($provider !== 'nvidia') {
            $this->info("AI provider {$provider} does not require a remote health check.");

            return self::SUCCESS;
        }

        $endpoint = $this->healthEndpoint();
        $token = (string) config('ai_tryon.nvidia.api_key');
        if ($endpoint === '' || $token === '') {
            $health->record(false, 'misconfigured', 'NVIDIA health endpoint or gateway token is missing.');
            $this->error('NVIDIA provider health configuration is incomplete.');

            return self::FAILURE;
        }

        try {
            $response = Http::withToken($token)->acceptJson()->timeout(8)->get($endpoint);
            if (! $response->successful()) {
                throw new \RuntimeException('Health endpoint returned HTTP '.$response->status().'.');
            }
            $health->record(true, 'ready');
            $this->info('NVIDIA provider is ready.');

            return self::SUCCESS;
        } catch (Throwable $exception) {
            $health->record(false, 'unavailable', $exception->getMessage());
            $this->error('NVIDIA provider is unavailable: '.$exception->getMessage());

            return self::FAILURE;
        }
    }

    private function healthEndpoint(): string
    {
        $configured = trim((string) config('ai_tryon.nvidia.health_endpoint'));
        if ($configured !== '') {
            return $configured;
        }

        return (string) preg_replace('#/v1/images/edits/?$#', '/v1/health/ready', trim((string) config('ai_tryon.nvidia.endpoint')));
    }
}
