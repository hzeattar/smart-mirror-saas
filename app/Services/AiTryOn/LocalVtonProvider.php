<?php

namespace App\Services\AiTryOn;

use App\Models\Product;
use App\Models\TryOnJob;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class LocalVtonProvider implements AiTryOnProvider
{
    public function generate(TryOnJob $job, Product $product, string $personImage, ?string $garmentImage): TryOnResult
    {
        $baseUrl = rtrim((string) config('ai_tryon.local_vton.base_url'), '/');
        if ($baseUrl === '') {
            throw new RuntimeException('Local VTON provider is not configured.');
        }

        $request = Http::timeout((int) config('ai_tryon.timeout_seconds', 120))
            ->acceptJson()
            ->attach('person_image', $personImage, 'person.jpg');

        if ($garmentImage) {
            $request = $request->attach('garment_image', $garmentImage, 'garment.png');
        }

        $response = $request->post($baseUrl.'/v1/try-on', [
            'model' => (string) config('ai_tryon.local_vton.model', 'idm-vton'),
            'job_id' => $job->public_id,
            'product_name' => $product->name,
            'garment_type' => $product->garment_type,
        ]);

        if (! $response->successful()) {
            throw new RuntimeException('Local VTON request failed: '.$response->status().' '.str($response->body())->limit(500)->toString());
        }

        $payload = $response->json();
        $base64 = data_get($payload, 'image') ?: data_get($payload, 'result.b64_json') ?: data_get($payload, 'data.0.b64_json');
        if (is_string($base64) && $base64 !== '') {
            $bytes = base64_decode(preg_replace('#^data:image/[^;]+;base64,#', '', $base64), true);
            if ($bytes !== false) {
                return new TryOnResult($bytes);
            }
        }

        $url = data_get($payload, 'result_url') ?: data_get($payload, 'data.0.url');
        if (is_string($url) && $url !== '') {
            $image = Http::timeout(60)->get($url);
            if ($image->successful()) {
                return new TryOnResult($image->body());
            }
        }

        throw new RuntimeException('Local VTON response did not include an image.');
    }
}
