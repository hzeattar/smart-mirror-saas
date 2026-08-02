<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Mirror;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MirrorKioskConfigController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $metadata = $mirror->metadata ?? [];
        $override = is_array($metadata['kiosk_config'] ?? null) ? $metadata['kiosk_config'] : [];

        return response()->json([
            'config' => [
                ...config('kiosk'),
                ...$override,
            ],
            'generated_at' => now()->toIso8601String(),
        ]);
    }
}
