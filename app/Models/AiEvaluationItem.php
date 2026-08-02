<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AiEvaluationItem extends Model
{
    use HasFactory;

    protected $fillable = [
        'ai_evaluation_id',
        'try_on_job_id',
        'product_id',
        'sample_image_path',
        'rating',
        'notes',
        'sort_order',
    ];

    protected function casts(): array
    {
        return [
            'sort_order' => 'integer',
        ];
    }

    public function evaluation(): BelongsTo
    {
        return $this->belongsTo(AiEvaluation::class, 'ai_evaluation_id');
    }

    public function job(): BelongsTo
    {
        return $this->belongsTo(TryOnJob::class, 'try_on_job_id');
    }

    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }
}
