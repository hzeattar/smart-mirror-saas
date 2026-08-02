<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\MirrorStatus;
use App\Enums\TryOnJobStatus;
use App\Http\Controllers\Controller;
use App\Jobs\GenerateTryOnImage;
use App\Models\AiEvaluation;
use App\Models\AiEvaluationItem;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\TryOnJob;
use App\Services\ProductReadinessService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class AiEvaluationController extends Controller
{
    public function __construct(private readonly ProductReadinessService $readiness) {}

    public function index(Request $request): JsonResponse
    {
        $evaluations = AiEvaluation::query()
            ->forTenant($request->user()->tenant_id)
            ->latest()
            ->paginate(12)
            ->through(fn (AiEvaluation $evaluation) => $this->present($evaluation->load(['items.job.product', 'items.product'])));

        return response()->json($evaluations);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'provider' => ['nullable', Rule::in(['mock', 'nvidia'])],
            'product_ids' => ['required', 'array', 'min:1', 'max:5'],
            'product_ids.*' => ['required', 'integer', 'distinct'],
            'sample_images' => ['required', 'array', 'min:1', 'max:20'],
            'sample_images.*' => ['required', 'image', 'max:12288'],
        ]);

        $tenantId = $request->user()->tenant_id;
        $productIds = collect($data['product_ids'])->map(fn ($id) => (int) $id)->values();
        $products = Product::query()
            ->forTenant($tenantId)
            ->whereIn('id', $productIds)
            ->with('sizingCharts')
            ->get()
            ->sortBy(fn (Product $product) => $productIds->search($product->id))
            ->values();
        abort_if($products->count() !== $productIds->count(), 422, 'One or more products are unavailable.');
        abort_if(
            $products->contains(fn (Product $product) => ! $this->readiness->availableForMirror($product)),
            422,
            'Evaluation products must be mirror-ready.'
        );

        $provider = (string) ($data['provider'] ?? config('ai_tryon.provider', 'mock'));
        $mirror = $this->evaluationMirror($tenantId);
        $publicId = (string) Str::uuid();
        $diskName = config('filesystems.default');

        $evaluation = AiEvaluation::query()->create([
            'public_id' => $publicId,
            'tenant_id' => $tenantId,
            'mirror_id' => $mirror->id,
            'provider' => $provider,
            'status' => 'queued',
            'sample_count' => count($data['sample_images']),
            'product_count' => $products->count(),
            'item_count' => count($data['sample_images']) * $products->count(),
        ]);

        $sort = 0;
        foreach ($data['sample_images'] as $sample) {
            $inputPath = $sample->store('try-on/evaluations/'.$publicId.'/samples', $diskName);
            foreach ($products as $product) {
                $job = TryOnJob::query()->create([
                    'public_id' => (string) Str::uuid(),
                    'tenant_id' => $tenantId,
                    'mirror_id' => $mirror->id,
                    'product_id' => $product->id,
                    'status' => TryOnJobStatus::Queued,
                    'provider' => $provider,
                    'input_image_path' => $inputPath,
                    'garment_image_path' => $product->texture_image_path ?: $product->base_image_path,
                    'queued_at' => now(),
                    'expires_at' => now()->addHours((int) config('ai_tryon.retention_hours', 24)),
                ]);
                AiEvaluationItem::query()->create([
                    'ai_evaluation_id' => $evaluation->id,
                    'try_on_job_id' => $job->id,
                    'product_id' => $product->id,
                    'sample_image_path' => $inputPath,
                    'sort_order' => $sort++,
                ]);
                GenerateTryOnImage::dispatch($job->id);
            }
        }

        return response()->json([
            'evaluation' => $this->present($evaluation->fresh(['items.job.product', 'items.product'])),
        ], 201);
    }

    public function show(Request $request, AiEvaluation $evaluation): JsonResponse
    {
        abort_unless($evaluation->tenant_id === $request->user()->tenant_id, 404);

        return response()->json(['evaluation' => $this->present($evaluation->load(['items.job.product', 'items.product']))]);
    }

    public function rateItem(Request $request, AiEvaluation $evaluation, AiEvaluationItem $item): JsonResponse
    {
        abort_unless($evaluation->tenant_id === $request->user()->tenant_id && $item->ai_evaluation_id === $evaluation->id, 404);
        $data = $request->validate([
            'rating' => ['required', Rule::in(['good', 'usable', 'bad'])],
            'notes' => ['nullable', 'string', 'max:1000'],
        ]);
        $item->update($data);

        return response()->json(['evaluation' => $this->present($evaluation->fresh(['items.job.product', 'items.product']))]);
    }

    private function evaluationMirror(int $tenantId): Mirror
    {
        return Mirror::query()->firstOrCreate(
            ['tenant_id' => $tenantId, 'location_name' => 'AI Evaluation Runner'],
            [
                'public_id' => (string) Str::uuid(),
                'pairing_code' => strtoupper(Str::random(8)),
                'status' => MirrorStatus::Pending,
                'metadata' => ['internal_runner' => true],
            ]
        );
    }

    private function present(AiEvaluation $evaluation): array
    {
        $this->syncEvaluation($evaluation);
        $disk = Storage::disk(config('filesystems.default'));
        $items = $evaluation->items->sortBy('sort_order')->values();
        $rated = $items->whereNotNull('rating')->count();
        $accepted = $items->whereIn('rating', ['good', 'usable'])->count();

        return [
            'id' => $evaluation->public_id,
            'provider' => $evaluation->provider,
            'status' => $evaluation->status,
            'sample_count' => $evaluation->sample_count,
            'product_count' => $evaluation->product_count,
            'item_count' => $evaluation->item_count,
            'completed_count' => $evaluation->completed_count,
            'failed_count' => $evaluation->failed_count,
            'good_count' => $evaluation->good_count,
            'usable_count' => $evaluation->usable_count,
            'bad_count' => $evaluation->bad_count,
            'usable_rate' => $rated > 0 ? round(($accepted / $rated) * 100, 1) : null,
            'production_gate_passed' => $rated > 0 && ($accepted / $rated) >= 0.70,
            'items' => $items->map(fn (AiEvaluationItem $item) => [
                'id' => $item->id,
                'sample_image_url' => $disk->url($item->sample_image_path),
                'product' => $item->product,
                'job' => $item->job ? [
                    'id' => $item->job->public_id,
                    'status' => $item->job->status->value,
                    'result_url' => $item->job->result_image_path ? url('/try-on-results/'.$item->job->public_id) : null,
                    'error' => $item->job->error,
                ] : null,
                'rating' => $item->rating,
                'notes' => $item->notes,
            ])->values(),
            'created_at' => $evaluation->created_at?->toIso8601String(),
            'completed_at' => $evaluation->completed_at?->toIso8601String(),
        ];
    }

    private function syncEvaluation(AiEvaluation $evaluation): void
    {
        $items = $evaluation->items;
        $jobs = $items->pluck('job')->filter();
        $completed = $jobs->where('status', TryOnJobStatus::Completed)->count();
        $failed = $jobs->where('status', TryOnJobStatus::Failed)->count();
        $processing = $jobs->where('status', TryOnJobStatus::Processing)->count();
        $terminal = $completed + $failed + $jobs->where('status', TryOnJobStatus::Cancelled)->count();
        $total = max(1, $items->count());
        $status = $evaluation->status;
        if ($completed > 0 && $terminal === $total) {
            $status = 'completed';
        } elseif ($terminal === $total && $completed === 0) {
            $status = 'failed';
        } elseif ($processing > 0 || $completed > 0 || $failed > 0) {
            $status = 'processing';
        }

        $evaluation->update([
            'status' => $status,
            'completed_count' => $completed,
            'failed_count' => $failed,
            'good_count' => $items->where('rating', 'good')->count(),
            'usable_count' => $items->where('rating', 'usable')->count(),
            'bad_count' => $items->where('rating', 'bad')->count(),
            'started_at' => $evaluation->started_at ?: ($processing > 0 || $completed > 0 || $failed > 0 ? now() : null),
            'completed_at' => $status === 'completed' ? ($evaluation->completed_at ?: now()) : null,
            'failed_at' => $status === 'failed' ? ($evaluation->failed_at ?: now()) : null,
            'error' => $status === 'failed' ? $jobs->firstWhere('error', '!=', null)?->error : null,
        ]);
        $evaluation->refresh();
    }
}
