<?php

namespace App\Services\AiTryOn;

use App\Models\Product;
use App\Models\TryOnJob;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class NvidiaTryOnProvider implements AiTryOnProvider
{
    public function generate(TryOnJob $job, Product $product, string $personImage, ?string $garmentImage): TryOnResult
    {
        $apiKey = (string) config('ai_tryon.nvidia.api_key');
        $model = (string) config('ai_tryon.nvidia.model');
        $baseUrl = rtrim((string) config('ai_tryon.nvidia.base_url'), '/');

        if ($apiKey === '' || $model === '') {
            throw new RuntimeException('NVIDIA try-on provider is not configured.');
        }

        $response = Http::withToken($apiKey)
            ->timeout((int) config('ai_tryon.timeout_seconds', 120))
            ->acceptJson()
            ->post($baseUrl.'/images/generations', [
                'model' => $model,
                'person_image' => base64_encode($personImage),
                'garment_image' => $garmentImage ? base64_encode($garmentImage) : null,
                'metadata' => [
                    'job_id' => $job->public_id,
                    'product_name' => $product->name,
                    'garment_type' => $product->garment_type,
                ],
            ]);

        if (! $response->successful()) {
            throw new RuntimeException('NVIDIA try-on request failed: '.$response->status().' '.$response->body());
        }

        $payload = $response->json();
        $base64 = data_get($payload, 'data.0.b64_json') ?: data_get($payload, 'image');
        if (is_string($base64) && $base64 !== '') {
            $bytes = base64_decode(preg_replace('#^data:image/[^;]+;base64,#', '', $base64), true);
            if ($bytes !== false) {
                return new TryOnResult($bytes);
            }
        }

        $url = data_get($payload, 'data.0.url') ?: data_get($payload, 'result_url');
        if (is_string($url) && $url !== '') {
            $image = Http::timeout(60)->get($url);
            if ($image->successful()) {
                return new TryOnResult($image->body());
            }
        }

        throw new RuntimeException('NVIDIA try-on response did not include an image.');
    }
}
