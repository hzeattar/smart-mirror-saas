<?php

namespace App\Http\Controllers\Api\Admin;

use App\Http\Controllers\Controller;
use App\Models\TryOnJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class TryOnJobController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $jobs = TryOnJob::query()
            ->forTenant($request->user()->tenant_id)
            ->when($request->filled('status'), fn ($query) => $query->where('status', $request->string('status')))
            ->when($request->filled('provider'), fn ($query) => $query->where('provider', $request->string('provider')))
            ->when($request->filled('mirror_id'), fn ($query) => $query->where('mirror_id', $request->integer('mirror_id')))
            ->when($request->filled('date_from'), fn ($query) => $query->whereDate('created_at', '>=', $request->date('date_from')))
            ->when($request->filled('date_to'), fn ($query) => $query->whereDate('created_at', '<=', $request->date('date_to')))
            ->with(['mirror:id,location_name,device_name', 'product:id,name,sku,garment_type'])
            ->latest()
            ->paginate(30)
            ->through(fn (TryOnJob $job) => [
                'id' => $job->public_id,
                'status' => $job->status->value,
                'provider' => $job->provider,
                'mirror' => $job->mirror,
                'product' => $job->product,
                'result_url' => $job->result_image_path ? url('/try-on-results/'.$job->public_id) : null,
                'error' => $job->error,
                'attempts' => $job->attempts,
                'created_at' => $job->created_at?->toIso8601String(),
                'started_at' => $job->started_at?->toIso8601String(),
                'completed_at' => $job->completed_at?->toIso8601String(),
                'failed_at' => $job->failed_at?->toIso8601String(),
                'processing_seconds' => $job->started_at && $job->completed_at ? $job->started_at->diffInSeconds($job->completed_at) : null,
                'expires_at' => $job->expires_at?->toIso8601String(),
            ]);

        return response()->json($jobs);
    }
}
