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
        $profile = is_array($metadata['kiosk_profile'] ?? null) ? $metadata['kiosk_profile'] : [];
        $legacyOverride = is_array($metadata['kiosk_config'] ?? null) ? $metadata['kiosk_config'] : [];
        $override = is_array($profile['config'] ?? null) ? $profile['config'] : $legacyOverride;
        $version = (int) ($profile['version'] ?? 1);
        $updatedAt = $profile['updated_at'] ?? $mirror->updated_at?->toIso8601String();

        return response()->json([
            'profile_version' => $version,
            'updated_at' => $updatedAt,
            'config' => [
                ...config('kiosk'),
                ...$override,
            ],
            'generated_at' => now()->toIso8601String(),
        ]);
    }
}
