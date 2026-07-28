<?php

namespace App\Models;

use App\Enums\CheckoutStatus;
use App\Enums\OrderType;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CheckoutSession extends Model
{
    use HasFactory;

    protected $fillable = [
        'public_id', 'tenant_id', 'mirror_id', 'token_hash', 'status', 'order_type',
        'cart', 'expires_at', 'completed_at', 'order_id',
    ];

    protected $hidden = ['token_hash'];

    protected function casts(): array
    {
        return [
            'status' => CheckoutStatus::class,
            'order_type' => OrderType::class,
            'cart' => 'array',
            'expires_at' => 'datetime',
            'completed_at' => 'datetime',
        ];
    }

    public function tenant(): BelongsTo { return $this->belongsTo(Tenant::class); }
    public function mirror(): BelongsTo { return $this->belongsTo(Mirror::class); }
    public function order(): BelongsTo { return $this->belongsTo(Order::class); }
}
