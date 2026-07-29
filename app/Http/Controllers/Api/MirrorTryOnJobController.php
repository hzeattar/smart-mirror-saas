<?php

namespace App\Http\Controllers\Api;

use App\Enums\TryOnJobStatus;
use App\Http\Controllers\Controller;
use App\Jobs\GenerateTryOnImage;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\SizingChart;
use App\Models\TryOnJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class MirrorTryOnJobController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'product_id' => ['required', 'integer'],
            'sizing_chart_id' => ['nullable', 'integer'],
            'snapshot' => ['required', 'image', 'max:12288'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $product = Product::query()
            ->forTenant($mirror->tenant_id)
            ->whereKey($data['product_id'])
            ->firstOrFail();

        if (isset($data['sizing_chart_id'])) {
            abort_unless(
                SizingChart::query()
                    ->where('product_id', $product->id)
                    ->whereKey($data['sizing_chart_id'])
                    ->exists(),
                422,
                'Selected size does not belong to the product.'
            );
        }

        $diskName = config('filesystems.default');
        $inputPath = $request->file('snapshot')->store('try-on/inputs', $diskName);
        $provider = (string) config('ai_tryon.provider', 'mock');
        $job = TryOnJob::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'product_id' => $product->id,
            'sizing_chart_id' => $data['sizing_chart_id'] ?? null,
            'status' => TryOnJobStatus::Queued,
            'provider' => $provider,
            'input_image_path' => $inputPath,
            'garment_image_path' => $product->texture_image_path ?: $product->base_image_path,
            'queued_at' => now(),
            'expires_at' => now()->addHours((int) config('ai_tryon.retention_hours', 24)),
        ]);

        GenerateTryOnImage::dispatch($job->id);

        return response()->json([
            'job' => $this->present($request, $job),
        ], 201);
    }

    public function show(Request $request, TryOnJob $job): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        abort_unless($job->mirror_id === $mirror->id && $job->tenant_id === $mirror->tenant_id, 404);

        return response()->json(['job' => $this->present($request, $job->fresh())]);
    }

    private function present(Request $request, TryOnJob $job): array
    {
        return [
            'id' => $job->public_id,
            'status' => $job->status->value,
            'provider' => $job->provider,
            'poll_url' => url('/api/mirror/try-on-jobs/'.$job->public_id),
            'result_url' => $job->result_image_path ? Storage::disk(config('filesystems.default'))->url($job->result_image_path) : null,
            'error' => $job->error,
            'created_at' => $job->created_at?->toIso8601String(),
            'completed_at' => $job->completed_at?->toIso8601String(),
            'expires_at' => $job->expires_at?->toIso8601String(),
        ];
    }
}
