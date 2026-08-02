<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\MirrorStatus;
use App\Enums\OrderStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Models\MirrorSessionEvent;
use App\Models\Order;
use App\Models\Product;
use App\Models\TryOnBatch;
use App\Models\TryOnJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $tenantId = $request->user()->tenant_id;

        return response()->json(['stats' => [
            'products' => Product::query()->forTenant($tenantId)->count(),
            'orders_today' => Order::query()->forTenant($tenantId)->whereDate('created_at', today())->count(),
            'pending_orders' => Order::query()->forTenant($tenantId)->whereNotIn('status', [OrderStatus::Completed, OrderStatus::Cancelled])->count(),
            'online_mirrors' => Mirror::query()->forTenant($tenantId)->where('status', MirrorStatus::Online)->count(),
            'revenue_today' => (float) Order::query()->forTenant($tenantId)->whereDate('created_at', today())->where('status', '!=', OrderStatus::Cancelled)->sum('total'),
            'mirror_sessions_today' => MirrorSessionEvent::query()->forTenant($tenantId)->whereDate('occurred_at', today())->distinct('mirror_id')->count('mirror_id'),
            'ai_batches_today' => TryOnBatch::query()->forTenant($tenantId)->whereDate('created_at', today())->count(),
            'ai_completion_rate' => $this->completionRate($tenantId),
            'ai_average_processing_seconds' => $this->averageProcessingSeconds($tenantId),
            'ai_failed_jobs' => TryOnJob::query()->forTenant($tenantId)->where('status', 'failed')->count(),
            'average_fps_today' => (float) round((float) MirrorSessionEvent::query()
                ->forTenant($tenantId)
                ->whereDate('occurred_at', today())
                ->whereNotNull('fps')
                ->avg('fps'), 1),
            'capture_completion_rate' => $this->captureCompletionRate($tenantId),
            'failed_jobs_by_provider' => TryOnJob::query()
                ->forTenant($tenantId)
                ->where('status', 'failed')
                ->selectRaw('provider, count(*) as total')
                ->groupBy('provider')
                ->pluck('total', 'provider'),
        ]]);
    }

    private function completionRate(int $tenantId): float
    {
        $total = TryOnJob::query()->forTenant($tenantId)->whereIn('status', ['completed', 'failed'])->count();
        if ($total === 0) {
            return 0.0;
        }

        $completed = TryOnJob::query()->forTenant($tenantId)->where('status', 'completed')->count();

        return round(($completed / $total) * 100, 1);
    }

    private function averageProcessingSeconds(int $tenantId): float
    {
        $jobs = TryOnJob::query()
            ->forTenant($tenantId)
            ->whereNotNull('started_at')
            ->whereNotNull('completed_at')
            ->latest()
            ->limit(200)
            ->get(['started_at', 'completed_at']);

        if ($jobs->isEmpty()) {
            return 0.0;
        }

        return round($jobs->avg(fn (TryOnJob $job) => $job->started_at->diffInSeconds($job->completed_at)), 1);
    }

    private function captureCompletionRate(int $tenantId): float
    {
        $started = MirrorSessionEvent::query()
            ->forTenant($tenantId)
            ->whereDate('occurred_at', today())
            ->where('event', 'hybrid_capture_started')
            ->count();

        if ($started === 0) {
            return 0.0;
        }

        $submitted = MirrorSessionEvent::query()
            ->forTenant($tenantId)
            ->whereDate('occurred_at', today())
            ->where('event', 'hybrid_batch_created')
            ->count();

        return round(($submitted / $started) * 100, 1);
    }
}
