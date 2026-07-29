<?php

namespace App\Jobs;

use App\Enums\TryOnJobStatus;
use App\Models\Product;
use App\Models\TryOnJob;
use App\Services\AiTryOn\AiTryOnProviderFactory;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Storage;
use Throwable;

class GenerateTryOnImage implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    public int $timeout = 180;

    public function __construct(public int $tryOnJobId) {}

    public function handle(AiTryOnProviderFactory $providers): void
    {
        try {
            $job = TryOnJob::query()->with('product')->findOrFail($this->tryOnJobId);
            if ($job->status === TryOnJobStatus::Cancelled) {
                return;
            }

            $job->update([
                'status' => TryOnJobStatus::Processing,
                'attempts' => $job->attempts + 1,
                'started_at' => $job->started_at ?: now(),
                'error' => null,
            ]);

            $disk = Storage::disk(config('filesystems.default'));
            $personImage = $disk->get($job->input_image_path);
            if ($personImage === null) {
                throw new \RuntimeException('Input image is missing.');
            }

            /** @var Product $product */
            $product = $job->product;
            $garmentPath = $job->garment_image_path ?: $product->texture_image_path ?: $product->base_image_path;
            $garmentImage = $garmentPath ? $disk->get($garmentPath) : null;

            $result = $providers->make($job->provider)->generate($job, $product, $personImage, $garmentImage);
            $extension = trim($result->extension, '.') ?: 'jpg';
            $resultPath = 'try-on/results/'.$job->public_id.'.'.$extension;
            $disk->put($resultPath, $result->bytes);

            $job->update([
                'status' => TryOnJobStatus::Completed,
                'result_image_path' => $resultPath,
                'completed_at' => now(),
                'failed_at' => null,
                'error' => null,
            ]);
        } catch (Throwable $exception) {
            $this->markFailed($exception);
        }
    }

    public function failed(?Throwable $exception): void
    {
        $this->markFailed($exception);
    }

    private function markFailed(?Throwable $exception): void
    {
        TryOnJob::query()->whereKey($this->tryOnJobId)->update([
            'status' => TryOnJobStatus::Failed,
            'failed_at' => now(),
            'error' => str($exception?->getMessage() ?: 'AI try-on generation failed.')->limit(1500)->toString(),
        ]);
    }
}
