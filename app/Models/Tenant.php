<?php

namespace App\Models;

use App\Enums\TenantStatus;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Tenant extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = ['name', 'domain', 'status'];

    protected function casts(): array
    {
        return ['status' => TenantStatus::class];
    }

    public function users(): HasMany
    {
        return $this->hasMany(User::class);
    }

    public function mirrors(): HasMany
    {
        return $this->hasMany(Mirror::class);
    }

    public function categories(): HasMany
    {
        return $this->hasMany(Category::class);
    }

    public function products(): HasMany
    {
        return $this->hasMany(Product::class);
    }

    public function orders(): HasMany
    {
        return $this->hasMany(Order::class);
    }

    public function checkoutSessions(): HasMany
    {
        return $this->hasMany(CheckoutSession::class);
    }

    public function tryOnJobs(): HasMany
    {
        return $this->hasMany(TryOnJob::class);
    }

    public function tryOnBatches(): HasMany
    {
        return $this->hasMany(TryOnBatch::class);
    }

    public function mirrorSessionEvents(): HasMany
    {
        return $this->hasMany(MirrorSessionEvent::class);
    }
}
