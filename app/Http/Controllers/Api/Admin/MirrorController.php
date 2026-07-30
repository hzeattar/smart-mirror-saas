<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\MirrorStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
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
                ->map(fn (Mirror $mirror) => [
                    ...$mirror->toArray(),
                    'latest_try_on_job' => $mirror->tryOnJobs->first()?->only([
                        'public_id',
                        'status',
                        'provider',
                        'created_at',
                        'completed_at',
                        'failed_at',
                        'error',
                    ]),
                    'latest_try_on_batch' => $mirror->tryOnBatches->first()?->only([
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
                    'latest_session_event' => $mirror->sessionEvents->first()?->only([
                        'event',
                        'fps',
                        'occurred_at',
                    ]),
                    'session_health' => $mirror->metadata['session_health'] ?? null,
                ]),
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
