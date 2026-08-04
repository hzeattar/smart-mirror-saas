<?php

namespace App\Http\Controllers\Api;

use App\Enums\LiveRestyleStatus;
use App\Http\Controllers\Controller;
use App\Models\LiveRestyleSession;
use App\Models\Mirror;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MirrorLiveRestyleConfigController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');

        return response()->json([
            'live_restyle' => $this->payload($mirror),
            'generated_at' => now()->toIso8601String(),
        ]);
    }

    public function payload(Mirror $mirror): array
    {
        $config = $this->mergedKioskConfig($mirror);
        $secondsUsedToday = $this->secondsUsedToday($mirror);
        $dailyLimit = (int) config('live_restyle.daily_seconds_limit', 120);
        $remainingSeconds = $dailyLimit > 0 ? max(0, $dailyLimit - $secondsUsedToday) : null;
        $globalEnabled = (bool) config('live_restyle.enabled', false);
        $profileEnabled = (bool) ($config['live_restyle_enabled'] ?? false);
        $model = (string) config('live_restyle.model', 'decart/lucy2-vton/realtime');
        $provider = (string) config('live_restyle.provider', 'fal');
        $maxSeconds = max(1, min(20, (int) config('live_restyle.max_seconds', 20)));

        $blockedReason = null;
        if (! $globalEnabled) {
            $blockedReason = 'global_disabled';
        } elseif (! $profileEnabled) {
            $blockedReason = 'profile_disabled';
        } elseif ($provider !== 'fal') {
            $blockedReason = 'unsupported_provider';
        } elseif ($model !== 'decart/lucy2-vton/realtime') {
            $blockedReason = 'unsupported_model';
        } elseif ($remainingSeconds !== null && $remainingSeconds <= 0) {
            $blockedReason = 'daily_limit_reached';
        }

        return [
            'enabled' => $blockedReason === null,
            'blocked_reason' => $blockedReason,
            'global_enabled' => $globalEnabled,
            'profile_enabled' => $profileEnabled,
            'provider' => $provider,
            'model' => $model,
            'max_seconds' => $maxSeconds,
            'daily_seconds_limit' => $dailyLimit,
            'seconds_used_today' => $secondsUsedToday,
            'remaining_seconds_today' => $remainingSeconds,
            'price_per_second_usd' => (float) config('live_restyle.price_per_second_usd', 0.02),
            'estimated_cost_today_usd' => round($secondsUsedToday * (float) config('live_restyle.price_per_second_usd', 0.02), 4),
            'local_proxy_url' => (string) config('live_restyle.local_proxy_url', 'http://127.0.0.1:8787'),
        ];
    }

    private function secondsUsedToday(Mirror $mirror): int
    {
        $sessions = LiveRestyleSession::query()
            ->where('mirror_id', $mirror->id)
            ->where('tenant_id', $mirror->tenant_id)
            ->whereDate('started_at', today())
            ->get(['status', 'max_seconds', 'duration_seconds', 'started_at', 'ended_at']);

        return (int) $sessions->sum(function (LiveRestyleSession $session): int {
            if ($session->duration_seconds !== null) {
                return min($session->duration_seconds, $session->max_seconds);
            }

            if ($session->status === LiveRestyleStatus::Active && $session->started_at) {
                return min($session->max_seconds, $session->started_at->diffInSeconds(now()));
            }

            return 0;
        });
    }

    private function mergedKioskConfig(Mirror $mirror): array
    {
        $profile = is_array($mirror->metadata['kiosk_profile'] ?? null) ? $mirror->metadata['kiosk_profile'] : [];
        $legacy = is_array($mirror->metadata['kiosk_config'] ?? null) ? $mirror->metadata['kiosk_config'] : [];
        $config = is_array($profile['config'] ?? null) ? $profile['config'] : $legacy;

        return [
            ...config('kiosk'),
            ...$config,
        ];
    }
}
