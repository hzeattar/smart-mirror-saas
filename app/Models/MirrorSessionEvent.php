<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class MirrorSessionEvent extends Model
{
    use HasFactory;

    protected $fillable = [
        'tenant_id',
        'mirror_id',
        'event',
        'fps',
        'payload',
        'occurred_at',
    ];

    protected function casts(): array
    {
        return [
            'fps' => 'decimal:2',
            'payload' => 'array',
            'occurred_at' => 'datetime',
        ];
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
