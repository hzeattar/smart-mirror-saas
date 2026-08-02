<?php

namespace App\Models;

use App\Enums\BackgroundRemovalStatus;
use App\Enums\ProductStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Product extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'tenant_id',
        'category_id',
        'sku',
        'name',
        'description',
        'garment_type',
        'fit_profile',
        'texture_anchor',
        'is_demo_asset',
        'asset_source',
        'asset_license',
        'image_qa',
        'base_image_url',
        'base_image_path',
        'texture_image_url',
        'texture_image_path',
        'unit_price',
        'currency',
        'status',
        'background_removal_status',
        'background_removal_error',
        'processed_at',
    ];

    protected function casts(): array
    {
        return [
            'unit_price' => 'decimal:2',
            'status' => ProductStatus::class,
            'background_removal_status' => BackgroundRemovalStatus::class,
            'fit_profile' => 'array',
            'texture_anchor' => 'array',
            'is_demo_asset' => 'boolean',
            'image_qa' => 'array',
            'processed_at' => 'datetime',
        ];
    }

    public function tenant(): BelongsTo
    {
        return $this->belongsTo(Tenant::class);
    }

    public function category(): BelongsTo
    {
        return $this->belongsTo(Category::class);
    }

    public function sizingCharts(): HasMany
    {
        return $this->hasMany(SizingChart::class)->orderBy('sort_order');
    }

    public function orderItems(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }

    public function tryOnJobs(): HasMany
    {
        return $this->hasMany(TryOnJob::class);
    }

    public function scopeForTenant(Builder $query, int $tenantId): Builder
    {
        return $query->where('tenant_id', $tenantId);
    }
}
