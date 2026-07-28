<?php

namespace App\Models;

use App\Enums\MirrorStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Mirror extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'public_id', 'tenant_id', 'pairing_code', 'api_token_hash', 'location_name',
        'device_name', 'status', 'paired_at', 'last_seen_at', 'app_version', 'metadata',
    ];
    protected $hidden = ['pairing_code', 'api_token_hash'];

    protected function casts(): array
    {
        return [
            'status' => MirrorStatus::class,
            'paired_at' => 'datetime',
            'last_seen_at' => 'datetime',
            'metadata' => 'array',
        ];
    }

    public function tenant(): BelongsTo { return $this->belongsTo(Tenant::class); }
    public function orders(): HasMany { return $this->hasMany(Order::class); }
    public function checkoutSessions(): HasMany { return $this->hasMany(CheckoutSession::class); }
    public function scopeForTenant(Builder $query, int $tenantId): Builder { return $query->where('tenant_id', $tenantId); }
}
