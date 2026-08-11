<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Services\AiTryOn\AiProviderHealth;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MirrorKioskConfigController extends Controller
{
    public function __construct(private readonly AiProviderHealth $aiHealth) {}

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

        $config = [
            ...config('kiosk'),
            ...$override,
        ];
        $health = $this->aiHealth->snapshot();
        $config['ai_available'] = (bool) ($config['ai_tryon_enabled'] ?? true) && (bool) $health['available'];

        return response()->json([
            'profile_version' => $version,
            'updated_at' => $updatedAt,
            'config' => $config,
            'ai_provider' => $health,
            'generated_at' => now()->toIso8601String(),
        ]);
    }
}
