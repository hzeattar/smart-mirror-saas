<?php

namespace App\Http\Controllers\Api\Admin;

use App\Http\Controllers\Controller;
use App\Models\TryOnJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class TryOnJobController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $jobs = TryOnJob::query()
            ->forTenant($request->user()->tenant_id)
            ->with(['mirror:id,location_name,device_name', 'product:id,name,sku,garment_type'])
            ->latest()
            ->paginate(30)
            ->through(fn (TryOnJob $job) => [
                'id' => $job->public_id,
                'status' => $job->status->value,
                'provider' => $job->provider,
                'mirror' => $job->mirror,
                'product' => $job->product,
                'result_url' => $job->result_image_path ? Storage::disk(config('filesystems.default'))->url($job->result_image_path) : null,
                'error' => $job->error,
                'attempts' => $job->attempts,
                'created_at' => $job->created_at?->toIso8601String(),
                'started_at' => $job->started_at?->toIso8601String(),
                'completed_at' => $job->completed_at?->toIso8601String(),
                'failed_at' => $job->failed_at?->toIso8601String(),
                'expires_at' => $job->expires_at?->toIso8601String(),
            ]);

        return response()->json($jobs);
    }
}
