<?php

namespace App\Jobs;

use App\Enums\BackgroundRemovalStatus;
use App\Models\Product;
use App\Services\BackgroundRemovalService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Storage;
use Throwable;

class ProcessGarmentImage implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    public int $timeout = 180;

    public function __construct(public int $productId) {}

    public function handle(BackgroundRemovalService $service): void
    {
        $product = Product::query()->findOrFail($this->productId);
        abort_unless($product->base_image_path, 422, 'Product has no source image.');
        $product->update(['background_removal_status' => BackgroundRemovalStatus::Processing, 'background_removal_error' => null]);

        $disk = Storage::disk(config('filesystems.default'));
        $outputPath = 'garments/textures/'.pathinfo($product->base_image_path, PATHINFO_FILENAME).'.png';
        $service->remove($product->base_image_path, $outputPath);

        $product->update([
            'texture_image_path' => $outputPath,
            'texture_image_url' => $disk->url($outputPath),
            'background_removal_status' => BackgroundRemovalStatus::Completed,
            'processed_at' => now(),
        ]);
    }

    public function failed(?Throwable $exception): void
    {
        Product::query()->whereKey($this->productId)->update([
            'background_removal_status' => BackgroundRemovalStatus::Failed,
            'background_removal_error' => $exception?->getMessage() ?: 'Background removal failed.',
        ]);
    }
}
