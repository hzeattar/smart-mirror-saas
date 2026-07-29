<?php

namespace App\Jobs;

use App\Enums\TryOnBatchStatus;
use App\Enums\TryOnJobStatus;
use App\Models\Product;
use App\Models\TryOnBatch;
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
            $this->syncBatch($job->try_on_batch_id);

            $disk = Storage::disk(config('filesystems.default'));
            $personImage = $disk->get($job->input_image_path);
            if ($personImage === null) {
                throw new \RuntimeException('Input image is missing.');
            }

            /** @var Product $product */
            $product = $job->product;
            $garmentPath = $job->garment_image_path ?: $product->texture_image_path ?: $product->base_image_path;
            $garmentImage = $garmentPath ? $disk->get($garmentPath) : null;
            if ($garmentImage === null) {
                $garmentUrl = $product->texture_image_url ?: $product->base_image_url;
                $publicPath = $garmentUrl && str_starts_with($garmentUrl, '/')
                    ? public_path(ltrim($garmentUrl, '/'))
                    : null;
                $garmentImage = $publicPath && is_file($publicPath) ? file_get_contents($publicPath) : null;
            }

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
            $this->syncBatch($job->try_on_batch_id);
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
        $this->syncBatch(TryOnJob::query()->whereKey($this->tryOnJobId)->value('try_on_batch_id'));
    }

    private function syncBatch(?int $batchId): void
    {
        if (! $batchId) {
            return;
        }

        $batch = TryOnBatch::query()->with('jobs')->find($batchId);
        if (! $batch) {
            return;
        }

        $jobs = $batch->jobs;
        $completed = $jobs->where('status', TryOnJobStatus::Completed)->count();
        $failed = $jobs->where('status', TryOnJobStatus::Failed)->count();
        $processing = $jobs->where('status', TryOnJobStatus::Processing)->count();
        $cancelled = $jobs->where('status', TryOnJobStatus::Cancelled)->count();
        $terminal = $completed + $failed + $cancelled;
        $total = max(1, $jobs->count());

        $status = $batch->status;
        if ($completed > 0 && $terminal === $total) {
            $status = TryOnBatchStatus::Completed;
        } elseif ($terminal === $total && $completed === 0) {
            $status = TryOnBatchStatus::Failed;
        } elseif ($processing > 0 || $completed > 0 || $failed > 0) {
            $status = TryOnBatchStatus::Processing;
        }

        $batch->update([
            'status' => $status,
            'completed_count' => $completed,
            'failed_count' => $failed,
            'started_at' => $batch->started_at ?: ($processing > 0 || $completed > 0 || $failed > 0 ? now() : null),
            'completed_at' => $status === TryOnBatchStatus::Completed ? now() : $batch->completed_at,
            'failed_at' => $status === TryOnBatchStatus::Failed ? now() : $batch->failed_at,
            'error' => $status === TryOnBatchStatus::Failed ? $jobs->firstWhere('error', '!=', null)?->error : null,
        ]);
    }
}
