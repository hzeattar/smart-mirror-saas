<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\MirrorStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class MirrorController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        return response()->json([
            'mirrors' => Mirror::query()
                ->forTenant($request->user()->tenant_id)
                ->with([
                    'tryOnJobs' => fn ($query) => $query->latest()->limit(1),
                    'tryOnBatches' => fn ($query) => $query->latest()->limit(1),
                    'sessionEvents' => fn ($query) => $query->latest('occurred_at')->limit(1),
                ])
                ->latest()
                ->get()
                ->map(fn (Mirror $mirror) => $this->present($mirror)),
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate(['location_name' => ['required', 'string', 'max:150']]);
        $mirror = Mirror::query()->create([
            'tenant_id' => $request->user()->tenant_id,
            'public_id' => (string) Str::uuid(),
            'pairing_code' => $this->uniqueCode(),
            'location_name' => $data['location_name'],
            'status' => MirrorStatus::Pending,
        ]);

        return response()->json(['mirror' => $mirror->makeVisible('pairing_code')], 201);
    }

    public function rotatePairingCode(Request $request, Mirror $mirror): JsonResponse
    {
        $this->authorizeTenant($request, $mirror);
        $mirror->update([
            'pairing_code' => $this->uniqueCode(),
            'api_token_hash' => null,
            'status' => MirrorStatus::Pending,
            'paired_at' => null,
        ]);

        return response()->json(['mirror' => $mirror->fresh()->makeVisible('pairing_code')]);
    }

    public function update(Request $request, Mirror $mirror): JsonResponse
    {
        $this->authorizeTenant($request, $mirror);
        $data = $request->validate([
            'location_name' => ['sometimes', 'string', 'max:150'],
            'status' => ['sometimes', Rule::enum(MirrorStatus::class)],
        ]);
        $mirror->update($data);

        return response()->json(['mirror' => $mirror->fresh()]);
    }

    public function updateKioskConfig(Request $request, Mirror $mirror): JsonResponse
    {
        $this->authorizeTenant($request, $mirror);
        $data = $request->validate([
            'config' => ['required', 'array'],
            'config.experience_mode' => ['sometimes', Rule::in(['hybrid', 'live'])],
            'config.outfit_count' => ['sometimes', 'integer', 'min:1', 'max:5'],
            'config.auto_start_delay_seconds' => ['sometimes', 'numeric', 'min:0.3', 'max:10'],
            'config.capture_burst_count' => ['sometimes', 'integer', 'min:1', 'max:10'],
            'config.capture_duration_seconds' => ['sometimes', 'numeric', 'min:0.5', 'max:8'],
            'config.gallery_timeout_seconds' => ['sometimes', 'numeric', 'min:5', 'max:300'],
            'config.poll_interval_seconds' => ['sometimes', 'numeric', 'min:1', 'max:15'],
            'config.pose_every_n' => ['sometimes', 'integer', 'min:1', 'max:6'],
            'config.hand_every_n' => ['sometimes', 'integer', 'min:1', 'max:6'],
            'config.kiosk_health_hud' => ['sometimes', 'boolean'],
            'config.gestures' => ['sometimes', 'array'],
            'config.gestures.cooldown_seconds' => ['sometimes', 'numeric', 'min:0.2', 'max:5'],
            'config.gestures.hold_seconds' => ['sometimes', 'numeric', 'min:0.2', 'max:3'],
            'config.gestures.swipe_distance' => ['sometimes', 'numeric', 'min:0.05', 'max:0.8'],
        ]);

        $metadata = $mirror->metadata ?? [];
        $profile = is_array($metadata['kiosk_profile'] ?? null) ? $metadata['kiosk_profile'] : [];
        $current = is_array($profile['config'] ?? null) ? $profile['config'] : [];
        $metadata['kiosk_profile'] = [
            'version' => (int) ($profile['version'] ?? 1) + 1,
            'updated_at' => now()->toIso8601String(),
            'config' => array_replace_recursive($current, $this->allowedKioskConfig($data['config'])),
        ];
        $mirror->update(['metadata' => $metadata]);

        return response()->json(['mirror' => $this->present($this->mirrorWithSummary($mirror->id, $request->user()->tenant_id))]);
    }

    private function present(Mirror $mirror): array
    {
        $latestJob = $mirror->tryOnJobs->first();
        $latestBatch = $mirror->tryOnBatches->first();
        $latestEvent = $mirror->sessionEvents->first();

        return [
            ...$mirror->toArray(),
            'latest_try_on_job' => $latestJob?->only([
                'public_id',
                'status',
                'provider',
                'created_at',
                'completed_at',
                'failed_at',
                'error',
            ]),
            'latest_try_on_batch' => $latestBatch?->only([
                'public_id',
                'status',
                'provider',
                'outfit_count',
                'completed_count',
                'failed_count',
                'created_at',
                'completed_at',
                'failed_at',
                'error',
            ]),
            'latest_session_event' => $latestEvent?->only([
                'event',
                'fps',
                'session_id',
                'severity',
                'occurred_at',
            ]),
            'session_health' => $mirror->metadata['session_health'] ?? null,
            'health' => $this->healthSummary($mirror, $latestJob, $latestBatch),
            'kiosk_profile' => $this->kioskProfile($mirror),
        ];
    }

    private function mirrorWithSummary(int $mirrorId, int $tenantId): Mirror
    {
        return Mirror::query()
            ->forTenant($tenantId)
            ->whereKey($mirrorId)
            ->with([
                'tryOnJobs' => fn ($query) => $query->latest()->limit(1),
                'tryOnBatches' => fn ($query) => $query->latest()->limit(1),
                'sessionEvents' => fn ($query) => $query->latest('occurred_at')->limit(1),
            ])
            ->firstOrFail();
    }

    private function healthSummary(Mirror $mirror, mixed $latestJob, mixed $latestBatch): array
    {
        $session = $mirror->metadata['session_health'] ?? [];
        $fps = (float) ($session['last_fps'] ?? 0);
        $lastSeenAt = $mirror->last_seen_at;
        $online = $lastSeenAt && $lastSeenAt->gt(now()->subSeconds(90));
        $lastEvent = (string) ($session['last_event'] ?? '');
        $badges = [$online ? 'Online' : 'Idle'];
        if (str_contains($lastEvent, 'camera_error')) {
            $badges[] = 'No Camera';
        }
        if ($fps > 0 && $fps < 15) {
            $badges[] = 'Low FPS';
        }
        if (str_contains($lastEvent, 'api') || str_contains($lastEvent, 'poll_error')) {
            $badges[] = 'API Errors';
        }
        if (($latestBatch?->status?->value ?? null) === 'failed' || ($latestJob?->status?->value ?? null) === 'failed') {
            $badges[] = 'AI Failing';
        }

        return [
            'status' => $badges[0],
            'badges' => array_values(array_unique($badges)),
            'last_fps' => $fps ?: null,
            'last_event' => $lastEvent ?: null,
            'last_event_at' => $session['last_event_at'] ?? null,
            'session_id' => $session['session_id'] ?? null,
            'severity' => $session['severity'] ?? null,
        ];
    }

    private function kioskProfile(Mirror $mirror): array
    {
        $profile = is_array($mirror->metadata['kiosk_profile'] ?? null) ? $mirror->metadata['kiosk_profile'] : [];
        $legacy = is_array($mirror->metadata['kiosk_config'] ?? null) ? $mirror->metadata['kiosk_config'] : [];
        $config = is_array($profile['config'] ?? null) ? $profile['config'] : $legacy;

        return [
            'version' => (int) ($profile['version'] ?? 1),
            'updated_at' => $profile['updated_at'] ?? $mirror->updated_at?->toIso8601String(),
            'config' => [
                ...config('kiosk'),
                ...$config,
            ],
        ];
    }

    private function allowedKioskConfig(array $config): array
    {
        return Arr::only($config, [
            'experience_mode',
            'outfit_count',
            'auto_start_delay_seconds',
            'capture_burst_count',
            'capture_duration_seconds',
            'gallery_timeout_seconds',
            'poll_interval_seconds',
            'pose_every_n',
            'hand_every_n',
            'kiosk_health_hud',
            'gestures',
        ]);
    }

    private function uniqueCode(): string
    {
        do {
            $code = strtoupper(Str::random(8));
        } while (Mirror::query()->where('pairing_code', $code)->exists());

        return $code;
    }

    private function authorizeTenant(Request $request, Mirror $mirror): void
    {
        abort_unless($mirror->tenant_id === $request->user()->tenant_id, 404);
    }
}
