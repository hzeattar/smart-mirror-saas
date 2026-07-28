<?php

namespace App\Http\Middleware;

use App\Enums\TenantStatus;
use App\Enums\UserStatus;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EnsureActiveUser
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();
        abort_unless($user, 401, 'Unauthenticated.');
        $user->loadMissing('tenant');
        abort_unless($user->status === UserStatus::Active, 403, 'User account is disabled.');
        abort_unless($user->tenant?->status === TenantStatus::Active, 403, 'Tenant is not active.');

        return $next($request);
    }
}
