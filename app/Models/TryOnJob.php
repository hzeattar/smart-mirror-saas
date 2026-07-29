<?php

namespace App\Models;

use App\Enums\TryOnJobStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TryOnJob extends Model
{
    use HasFactory;

    protected $fillable = [
        'public_id',
        'tenant_id',
        'mirror_id',
        'product_id',
        'sizing_chart_id',
        'status',
        'provider',
        'input_image_path',
        'garment_image_path',
        'result_image_path',
        'error',
        'attempts',
        'queued_at',
        'started_at',
        'completed_at',
        'failed_at',
        'expires_at',
    ];

    protected function casts(): array
    {
        return [
            'status' => TryOnJobStatus::class,
            'attempts' => 'integer',
            'queued_at' => 'datetime',
            'started_at' => 'datetime',
            'completed_at' => 'datetime',
            'failed_at' => 'datetime',
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

    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }

    public function sizingChart(): BelongsTo
    {
        return $this->belongsTo(SizingChart::class);
    }

    public function scopeForTenant(Builder $query, int $tenantId): Builder
    {
        return $query->where('tenant_id', $tenantId);
    }
}
