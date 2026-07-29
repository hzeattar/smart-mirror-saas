<?php

namespace App\Http\Controllers\Api\Admin;

use App\Http\Controllers\Controller;
use App\Models\TryOnBatch;
use App\Models\TryOnJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class TryOnBatchController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $batches = TryOnBatch::query()
            ->forTenant($request->user()->tenant_id)
            ->with(['mirror:id,location_name,device_name', 'jobs.product:id,name,sku,garment_type,unit_price,currency'])
            ->latest()
            ->paginate(20)
            ->through(fn (TryOnBatch $batch) => [
                'id' => $batch->public_id,
                'status' => $batch->status->value,
                'provider' => $batch->provider,
                'mirror' => $batch->mirror,
                'outfit_count' => $batch->outfit_count,
                'completed_count' => $batch->completed_count,
                'failed_count' => $batch->failed_count,
                'jobs' => $batch->jobs->map(fn (TryOnJob $job) => [
                    'id' => $job->public_id,
                    'status' => $job->status->value,
                    'product' => $job->product,
                    'result_url' => $job->result_image_path ? url('/try-on-results/'.$job->public_id) : null,
                    'error' => $job->error,
                ])->values(),
                'error' => $batch->error,
                'created_at' => $batch->created_at?->toIso8601String(),
                'started_at' => $batch->started_at?->toIso8601String(),
                'completed_at' => $batch->completed_at?->toIso8601String(),
                'failed_at' => $batch->failed_at?->toIso8601String(),
                'expires_at' => $batch->expires_at?->toIso8601String(),
            ]);

        return response()->json($batches);
    }
}
