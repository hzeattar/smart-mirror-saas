<?php

namespace App\Services\AiTryOn;

use App\Models\Product;
use App\Models\TryOnJob;

interface AiTryOnProvider
{
    public function generate(TryOnJob $job, Product $product, string $personImage, ?string $garmentImage): TryOnResult;
}
