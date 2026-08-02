<?php

namespace App\Http\Controllers\Api;

use App\Enums\TryOnBatchStatus;
use App\Enums\TryOnJobStatus;
use App\Http\Controllers\Controller;
use App\Jobs\GenerateTryOnImage;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\SizingChart;
use App\Models\TryOnBatch;
use App\Models\TryOnJob;
use App\Services\ProductReadinessService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Collection;
use Illuminate\Support\Str;

class MirrorTryOnBatchController extends Controller
{
    public function __construct(private readonly ProductReadinessService $readiness) {}

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'product_ids' => ['required', 'array', 'min:1', 'max:5'],
            'product_ids.*' => ['required', 'integer', 'distinct'],
            'sizing_chart_id' => ['nullable', 'integer'],
            'snapshot' => ['required', 'image', 'max:12288'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $productIds = collect($data['product_ids'])->map(fn ($id) => (int) $id)->values();
        /** @var Collection<int, Product> $products */
        $products = Product::query()
            ->forTenant($mirror->tenant_id)
            ->whereIn('id', $productIds)
            ->get()
            ->sortBy(fn (Product $product) => $productIds->search($product->id))
            ->values();

        abort_if($products->count() !== $productIds->count(), 422, 'One or more products are unavailable.');
        abort_if(
            $products->contains(fn (Product $product) => ! $this->readiness->availableForMirror($product)),
            422,
            'One or more products are not production-ready for the mirror.'
        );

        $sizingChartId = isset($data['sizing_chart_id']) ? (int) $data['sizing_chart_id'] : null;
        if ($sizingChartId) {
            abort_unless(
                SizingChart::query()
                    ->whereIn('product_id', $products->pluck('id'))
                    ->whereKey($sizingChartId)
                    ->exists(),
                422,
                'Selected size does not belong to the requested products.'
            );
        }

        $diskName = config('filesystems.default');
        $batchId = (string) Str::uuid();
        $inputPath = $request->file('snapshot')->store('try-on/batches/'.$batchId, $diskName);
        $provider = (string) config('ai_tryon.provider', 'mock');

        $batch = TryOnBatch::query()->create([
            'public_id' => $batchId,
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'sizing_chart_id' => $sizingChartId,
            'status' => TryOnBatchStatus::Queued,
            'provider' => $provider,
            'input_image_path' => $inputPath,
            'outfit_count' => $products->count(),
            'queued_at' => now(),
            'expires_at' => now()->addHours((int) config('ai_tryon.retention_hours', 24)),
        ]);

        foreach ($products as $product) {
            $productSizingChartId = $sizingChartId && $product->sizingCharts()->whereKey($sizingChartId)->exists()
                ? $sizingChartId
                : null;
            $job = TryOnJob::query()->create([
                'public_id' => (string) Str::uuid(),
                'try_on_batch_id' => $batch->id,
                'tenant_id' => $mirror->tenant_id,
                'mirror_id' => $mirror->id,
                'product_id' => $product->id,
                'sizing_chart_id' => $productSizingChartId,
                'status' => TryOnJobStatus::Queued,
                'provider' => $provider,
                'input_image_path' => $inputPath,
                'garment_image_path' => $product->texture_image_path ?: $product->base_image_path,
                'queued_at' => now(),
                'expires_at' => $batch->expires_at,
            ]);

            GenerateTryOnImage::dispatch($job->id);
        }

        return response()->json([
            'batch' => $this->present($request, $batch->fresh(['jobs.product'])),
        ], 201);
    }

    public function show(Request $request, TryOnBatch $batch): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        abort_unless($batch->mirror_id === $mirror->id && $batch->tenant_id === $mirror->tenant_id, 404);

        return response()->json(['batch' => $this->present($request, $batch->fresh(['jobs.product']))]);
    }

    private function present(Request $request, TryOnBatch $batch): array
    {
        $jobs = $batch->jobs;
        $completed = $jobs->where('status', TryOnJobStatus::Completed)->count();
        $failed = $jobs->where('status', TryOnJobStatus::Failed)->count();
        $terminal = $completed + $failed + $jobs->where('status', TryOnJobStatus::Cancelled)->count();
        $status = $batch->status;

        if ($jobs->isNotEmpty()) {
            if ($completed > 0 && $terminal === $jobs->count()) {
                $status = TryOnBatchStatus::Completed;
            } elseif ($terminal === $jobs->count() && $completed === 0) {
                $status = TryOnBatchStatus::Failed;
            } elseif ($completed > 0 || $failed > 0 || $jobs->contains('status', TryOnJobStatus::Processing)) {
                $status = TryOnBatchStatus::Processing;
            }
        }

        if ($status !== $batch->status || $completed !== $batch->completed_count || $failed !== $batch->failed_count) {
            $batch->update([
                'status' => $status,
                'completed_count' => $completed,
                'failed_count' => $failed,
            ]);
        }

        return [
            'id' => $batch->public_id,
            'status' => $status->value,
            'provider' => $batch->provider,
            'poll_url' => url('/api/mirror/try-on-batches/'.$batch->public_id),
            'outfit_count' => $batch->outfit_count,
            'completed_count' => $completed,
            'failed_count' => $failed,
            'recommended_size' => $batch->sizingChart?->size_label,
            'jobs' => $jobs->map(fn (TryOnJob $job) => [
                'id' => $job->public_id,
                'status' => $job->status->value,
                'product' => $job->product ? [
                    'id' => $job->product->id,
                    'sku' => $job->product->sku,
                    'name' => $job->product->name,
                    'garment_type' => $job->product->garment_type,
                    'price' => (float) $job->product->unit_price,
                    'currency' => $job->product->currency,
                ] : null,
                'result_url' => $job->result_image_path ? url('/try-on-results/'.$job->public_id) : null,
                'error' => $job->error,
                'created_at' => $job->created_at?->toIso8601String(),
                'completed_at' => $job->completed_at?->toIso8601String(),
            ])->values(),
            'error' => $batch->error,
            'created_at' => $batch->created_at?->toIso8601String(),
            'completed_at' => $batch->completed_at?->toIso8601String(),
            'expires_at' => $batch->expires_at?->toIso8601String(),
        ];
    }
}
