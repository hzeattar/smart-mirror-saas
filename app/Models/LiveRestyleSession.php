<?php

namespace App\Models;

use App\Enums\LiveRestyleStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LiveRestyleSession extends Model
{
    use HasFactory;

    protected $fillable = [
        'public_id',
        'tenant_id',
        'mirror_id',
        'provider',
        'model',
        'status',
        'max_seconds',
        'daily_seconds_limit',
        'duration_seconds',
        'estimated_cost_usd',
        'error',
        'metadata',
        'started_at',
        'ended_at',
        'expires_at',
    ];

    protected function casts(): array
    {
        return [
            'status' => LiveRestyleStatus::class,
            'max_seconds' => 'integer',
            'daily_seconds_limit' => 'integer',
            'duration_seconds' => 'integer',
            'estimated_cost_usd' => 'float',
            'metadata' => 'array',
            'started_at' => 'datetime',
            'ended_at' => 'datetime',
            'expires_at' => 'datetime',
        ];
    }

    public function getRouteKeyName(): string
    {
        return 'public_id';
    }

    public function tenant(): BelongsTo
    {
        return $this->belongsTo(Tenant::class);
    }

    public function mirror(): BelongsTo
    {
        return $this->belongsTo(Mirror::class);
    }

    public function scopeForTenant(Builder $query, int $tenantId): Builder
    {
        return $query->where('tenant_id', $tenantId);
    }
}
