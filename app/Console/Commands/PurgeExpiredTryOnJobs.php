<?php

namespace App\Console\Commands;

use App\Models\TryOnBatch;
use App\Models\TryOnJob;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Storage;

class PurgeExpiredTryOnJobs extends Command
{
    protected $signature = 'tryon:purge-expired';

    protected $description = 'Delete expired AI try-on media and job records.';

    public function handle(): int
    {
        $disk = Storage::disk(config('filesystems.default'));
        $count = 0;

        TryOnBatch::query()
            ->whereNotNull('expires_at')
            ->where('expires_at', '<', now())
            ->with('jobs')
            ->chunkById(100, function ($batches) use ($disk, &$count): void {
                foreach ($batches as $batch) {
                    foreach ($batch->jobs as $job) {
                        foreach ([$job->result_image_path] as $path) {
                            if ($path) {
                                $disk->delete($path);
                            }
                        }
                        $job->delete();
                    }
                    if ($batch->input_image_path) {
                        $disk->delete($batch->input_image_path);
                    }
                    $batch->delete();
                    $count++;
                }
            });

        TryOnJob::query()
            ->whereNull('try_on_batch_id')
            ->whereNotNull('expires_at')
            ->where('expires_at', '<', now())
            ->chunkById(100, function ($jobs) use ($disk, &$count): void {
                foreach ($jobs as $job) {
                    foreach ([$job->input_image_path, $job->result_image_path] as $path) {
                        if ($path) {
                            $disk->delete($path);
                        }
                    }
                    $job->delete();
                    $count++;
                }
            });

        $this->info("Purged {$count} expired try-on jobs.");

        return self::SUCCESS;
    }
}
