<?php

namespace App\Http\Controllers\Api;

use App\Enums\MirrorStatus;
use App\Enums\TenantStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class MirrorAuthController extends Controller
{
    public function pair(Request $request): JsonResponse
    {
        $data = $request->validate([
            'pairing_code' => ['required', 'string', 'max:16'],
            'device_name' => ['required', 'string', 'max:150'],
            'app_version' => ['nullable', 'string', 'max:50'],
        ]);

        $mirror = Mirror::query()->with('tenant')->where('pairing_code', strtoupper($data['pairing_code']))->first();
        if (! $mirror || $mirror->tenant?->status !== TenantStatus::Active) {
            throw ValidationException::withMessages(['pairing_code' => ['Pairing code is invalid or inactive.']]);
        }
        abort_if($mirror->status === MirrorStatus::Disabled, 403, 'Mirror is disabled.');

        $plainToken = Str::random(64);
        $mirror->forceFill([
            'public_id' => $mirror->public_id ?: (string) Str::uuid(),
            'api_token_hash' => hash('sha256', $plainToken),
            'device_name' => $data['device_name'],
            'app_version' => $data['app_version'] ?? null,
            'status' => MirrorStatus::Paired,
            'paired_at' => now(),
            'last_seen_at' => now(),
        ])->save();

        return response()->json([
            'token' => $plainToken,
            'mirror' => [
                'id' => $mirror->id,
                'public_id' => $mirror->public_id,
                'location_name' => $mirror->location_name,
                'tenant' => ['id' => $mirror->tenant->id, 'name' => $mirror->tenant->name],
            ],
        ]);
    }
}
