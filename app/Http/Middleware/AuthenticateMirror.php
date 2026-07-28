<?php

namespace App\Http\Middleware;

use App\Enums\MirrorStatus;
use App\Models\Mirror;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AuthenticateMirror
{
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->bearerToken();
        abort_unless($token, 401, 'Mirror token is missing.');

        $mirror = Mirror::query()
            ->with('tenant')
            ->where('api_token_hash', hash('sha256', $token))
            ->first();

        abort_unless($mirror, 401, 'Mirror token is invalid.');
        abort_if($mirror->status === MirrorStatus::Disabled, 403, 'Mirror is disabled.');
        abort_unless($mirror->tenant?->status?->value === 'active', 403, 'Tenant is not active.');

        $mirror->forceFill([
            'last_seen_at' => now(),
            'status' => MirrorStatus::Online,
        ])->saveQuietly();

        $request->attributes->set('mirror', $mirror);
        $request->attributes->set('tenant', $mirror->tenant);

        return $next($request);
    }
}
