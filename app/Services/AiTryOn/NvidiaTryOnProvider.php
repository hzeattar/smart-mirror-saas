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
        $endpoint = (string) config('ai_tryon.nvidia.endpoint');
        $model = (string) config('ai_tryon.nvidia.model');

        if ($apiKey === '' || $endpoint === '' || $model === '') {
            throw new RuntimeException('NVIDIA try-on provider is not configured.');
        }

        $images = [$this->dataUri($personImage)];
        if ($garmentImage !== null && $garmentImage !== '') {
            $images[] = $this->dataUri($garmentImage);
        }

        $response = Http::withToken($apiKey)
            ->timeout(min(90, max(10, (int) config('ai_tryon.timeout_seconds', 90))))
            ->acceptJson()
            ->asJson()
            ->post($endpoint, [
                'model' => $model,
                'prompt' => $this->prompt($product, $garmentImage !== null && $garmentImage !== ''),
                'response_format' => 'b64_json',
                'image' => $images,
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

    private function dataUri(string $bytes): string
    {
        $mime = (new \finfo(FILEINFO_MIME_TYPE))->buffer($bytes);
        if (! in_array($mime, ['image/jpeg', 'image/png'], true)) {
            $mime = 'image/jpeg';
        }

        return 'data:'.$mime.';base64,'.base64_encode($bytes);
    }

    private function prompt(Product $product, bool $hasGarmentImage): string
    {
        $configured = trim((string) config('ai_tryon.nvidia.prompt'));
        if ($configured !== '') {
            return $configured;
        }

        $garmentReference = $hasGarmentImage
            ? 'The first image is the customer and the second image is the exact garment reference.'
            : 'Use the product description as the garment reference.';

        return implode(' ', [
            'Create a photorealistic retail virtual try-on image.',
            $garmentReference,
            'Dress the customer in the referenced garment while preserving their identity, face, hair, body shape, pose, hands, background, and lighting.',
            'Preserve the garment color, material, texture, logos, cut, and proportions accurately.',
            'Do not add text, watermarks, extra people, or unrelated objects.',
            'Product: '.$product->name.'.',
            $product->garment_type ? 'Garment type: '.$product->garment_type.'.' : '',
        ]);
    }
}
