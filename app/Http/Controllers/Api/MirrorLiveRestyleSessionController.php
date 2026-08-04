<?php

namespace App\Http\Controllers\Api;

use App\Enums\LiveRestyleStatus;
use App\Http\Controllers\Controller;
use App\Models\LiveRestyleSession;
use App\Models\Mirror;
use App\Models\Product;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class MirrorLiveRestyleSessionController extends Controller
{
    public function __construct(private readonly MirrorLiveRestyleConfigController $configController) {}

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'product_id' => ['nullable', 'integer'],
            'reference_image_url' => ['nullable', 'url', 'max:2048'],
            'prompt' => ['nullable', 'string', 'max:500'],
            'max_seconds' => ['nullable', 'integer', 'min:1', 'max:20'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $config = $this->configController->payload($mirror);
        if (! $config['enabled']) {
            return response()->json([
                'message' => 'Live restyle is not enabled for this mirror.',
                'blocked_reason' => $config['blocked_reason'],
                'live_restyle' => $config,
            ], $config['blocked_reason'] === 'daily_limit_reached' ? 429 : 403);
        }

        $product = null;
        if (! empty($data['product_id'])) {
            $product = Product::query()
                ->forTenant($mirror->tenant_id)
                ->whereKey((int) $data['product_id'])
                ->first();

            abort_unless($product, 422, 'Selected product is unavailable.');
        }

        $maxSeconds = min(
            20,
            (int) ($data['max_seconds'] ?? $config['max_seconds']),
            (int) $config['max_seconds']
        );
        if ($config['remaining_seconds_today'] !== null) {
            $maxSeconds = min($maxSeconds, (int) $config['remaining_seconds_today']);
        }

        abort_if($maxSeconds < 1, 429, 'Daily live restyle limit is exhausted.');

        $session = LiveRestyleSession::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'provider' => $config['provider'],
            'model' => $config['model'],
            'status' => LiveRestyleStatus::Active,
            'max_seconds' => $maxSeconds,
            'daily_seconds_limit' => $config['daily_seconds_limit'],
            'metadata' => [
                'product_id' => $product?->id,
                'product_sku' => $product?->sku,
                'reference_image_url' => $data['reference_image_url'] ?? null,
                'prompt' => $data['prompt'] ?? null,
            ],
            'started_at' => now(),
            'expires_at' => now()->addMinutes(5),
        ]);

        return response()->json([
            'session' => $this->present($session),
        ], 201);
    }

    public function update(Request $request, LiveRestyleSession $session): JsonResponse
    {
        $data = $request->validate([
            'status' => ['required', Rule::in([
                LiveRestyleStatus::Completed->value,
                LiveRestyleStatus::Failed->value,
                LiveRestyleStatus::Cancelled->value,
            ])],
            'duration_seconds' => ['nullable', 'integer', 'min:0', 'max:20'],
            'error' => ['nullable', 'string', 'max:500'],
            'metadata' => ['nullable', 'array'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        abort_unless($session->mirror_id === $mirror->id && $session->tenant_id === $mirror->tenant_id, 404);

        $durationSeconds = (int) ($data['duration_seconds'] ?? $session->started_at?->diffInSeconds(now()) ?? 0);
        $durationSeconds = min($session->max_seconds, max(0, $durationSeconds));
        $price = (float) config('live_restyle.price_per_second_usd', 0.02);
        $metadata = is_array($session->metadata) ? $session->metadata : [];

        if (isset($data['metadata'])) {
            $metadata = array_replace_recursive($metadata, $data['metadata']);
        }

        $session->update([
            'status' => LiveRestyleStatus::from($data['status']),
            'duration_seconds' => $durationSeconds,
            'estimated_cost_usd' => round($durationSeconds * $price, 4),
            'error' => isset($data['error']) ? Str::limit($data['error'], 500, '') : $session->error,
            'metadata' => $metadata,
            'ended_at' => now(),
        ]);

        return response()->json([
            'session' => $this->present($session->fresh()),
        ]);
    }

    private function present(LiveRestyleSession $session): array
    {
        return [
            'id' => $session->public_id,
            'status' => $session->status->value,
            'provider' => $session->provider,
            'model' => $session->model,
            'max_seconds' => $session->max_seconds,
            'duration_seconds' => $session->duration_seconds,
            'estimated_cost_usd' => (float) $session->estimated_cost_usd,
            'started_at' => $session->started_at?->toIso8601String(),
            'ended_at' => $session->ended_at?->toIso8601String(),
            'expires_at' => $session->expires_at?->toIso8601String(),
        ];
    }
}
