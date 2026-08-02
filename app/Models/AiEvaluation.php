<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AiEvaluation extends Model
{
    use HasFactory;

    protected $fillable = [
        'public_id',
        'tenant_id',
        'mirror_id',
        'provider',
        'status',
        'sample_count',
        'product_count',
        'item_count',
        'completed_count',
        'failed_count',
        'good_count',
        'usable_count',
        'bad_count',
        'error',
        'started_at',
        'completed_at',
        'failed_at',
    ];

    protected function casts(): array
    {
        return [
            'sample_count' => 'integer',
            'product_count' => 'integer',
            'item_count' => 'integer',
            'completed_count' => 'integer',
            'failed_count' => 'integer',
            'good_count' => 'integer',
            'usable_count' => 'integer',
            'bad_count' => 'integer',
            'started_at' => 'datetime',
            'completed_at' => 'datetime',
            'failed_at' => 'datetime',
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

    public function items(): HasMany
    {
        return $this->hasMany(AiEvaluationItem::class);
    }

    public function scopeForTenant(Builder $query, int $tenantId): Builder
    {
        return $query->where('tenant_id', $tenantId);
    }
}
