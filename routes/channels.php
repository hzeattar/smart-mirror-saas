<?php

use App\Models\User;
use Illuminate\Support\Facades\Broadcast;

Broadcast::channel('tenant.{tenantId}.orders', function (User $user, int $tenantId): bool {
    return $user->tenant_id === $tenantId;
});
