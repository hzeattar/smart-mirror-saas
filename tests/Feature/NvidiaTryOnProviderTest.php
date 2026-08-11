<?php

namespace Tests\Feature;

use App\Models\Product;
use App\Models\TryOnJob;
use App\Services\AiTryOn\NvidiaTryOnProvider;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class NvidiaTryOnProviderTest extends TestCase
{
    public function test_it_uses_the_nvidia_openai_compatible_image_edit_contract(): void
    {
        config([
            'ai_tryon.nvidia.api_key' => 'test-key',
            'ai_tryon.nvidia.endpoint' => 'https://nim.example.test/v1/images/edits',
            'ai_tryon.nvidia.model' => 'flux.2-klein-4b',
            'ai_tryon.nvidia.prompt' => null,
        ]);

        Http::fake([
            'https://nim.example.test/*' => Http::response([
                'data' => [['b64_json' => base64_encode('generated-image')]],
            ]),
        ]);

        $result = (new NvidiaTryOnProvider)->generate(
            new TryOnJob(['public_id' => 'job-123']),
            new Product(['name' => 'Blue Jacket', 'garment_type' => 'jacket']),
            'person-image',
            'garment-image',
        );

        $this->assertSame('generated-image', $result->bytes);

        Http::assertSent(function (Request $request): bool {
            $data = $request->data();

            return $request->url() === 'https://nim.example.test/v1/images/edits'
                && $request->hasHeader('Authorization', 'Bearer test-key')
                && $request->hasHeader('Content-Type', 'application/json')
                && $data['model'] === 'flux.2-klein-4b'
                && $data['response_format'] === 'b64_json'
                && str_contains($data['prompt'], 'exact garment reference')
                && count($data['image']) === 2
                && $data['image'][0] === 'data:image/jpeg;base64,'.base64_encode('person-image')
                && $data['image'][1] === 'data:image/jpeg;base64,'.base64_encode('garment-image');
        });
    }
}
