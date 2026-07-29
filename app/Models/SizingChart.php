<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class SizingChart extends Model
{
    use HasFactory;

    protected $fillable = [
        'product_id',
        'size_label',
        'shoulder_width_cm',
        'chest_width_cm',
        'waist_width_cm',
        'hip_width_cm',
        'sleeve_length_cm',
        'fit_ease_cm',
        'height_cm',
        'sort_order',
    ];

    protected function casts(): array
    {
        return [
            'shoulder_width_cm' => 'decimal:2',
            'chest_width_cm' => 'decimal:2',
            'waist_width_cm' => 'decimal:2',
            'hip_width_cm' => 'decimal:2',
            'sleeve_length_cm' => 'decimal:2',
            'fit_ease_cm' => 'decimal:2',
            'height_cm' => 'decimal:2',
            'sort_order' => 'integer',
        ];
    }

    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }

    public function orderItems(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }
}
