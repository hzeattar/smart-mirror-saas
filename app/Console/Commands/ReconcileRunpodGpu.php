<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Throwable;

class ReconcileRunpodGpu extends Command
{
    protected $signature = 'runpod:reconcile {--dry-run : Report the desired action without changing the pod}';

    protected $description = 'Start or stop the pilot NVIDIA GPU pod according to store hours.';

    public function handle(): int
    {
        if (! config('runpod.enabled')) {
            $this->info('RunPod scheduling is disabled.');

            return self::SUCCESS;
        }

        $podId = trim((string) config('runpod.pod_id'));
        $apiKey = trim((string) config('runpod.api_key'));
        if ($podId === '' || $apiKey === '') {
            $this->error('RUNPOD_POD_ID and RUNPOD_API_KEY are required.');

            return self::FAILURE;
        }

        try {
            $response = $this->client()->get('/pods/'.$podId)->throw()->json();
            $status = strtoupper((string) ($response['desiredStatus'] ?? $response['status'] ?? 'UNKNOWN'));
            $desired = $this->shouldRunNow() ? 'RUNNING' : 'STOPPED';
            $action = $this->action($status, $desired);
            $this->info("RunPod status={$status}, desired={$desired}, action={$action}.");

            if ($action === 'none' || $this->option('dry-run')) {
                return self::SUCCESS;
            }

            $this->client()->post('/pods/'.$podId.'/'.$action)->throw();
            $this->info("RunPod {$action} request accepted.");

            return self::SUCCESS;
        } catch (Throwable $exception) {
            $this->error('RunPod reconciliation failed: '.$exception->getMessage());

            return self::FAILURE;
        }
    }

    private function client(): PendingRequest
    {
        return Http::baseUrl(rtrim((string) config('runpod.api_base'), '/'))
            ->withToken((string) config('runpod.api_key'))
            ->acceptJson()
            ->timeout(15)
            ->retry(2, 500);
    }

    private function shouldRunNow(): bool
    {
        $timezone = (string) config('runpod.timezone', 'Africa/Cairo');
        $now = Carbon::now($timezone);
        $start = Carbon::createFromFormat('H:i', (string) config('runpod.active_start', '09:30'), $timezone)->setDateFrom($now);
        $end = Carbon::createFromFormat('H:i', (string) config('runpod.active_end', '22:15'), $timezone)->setDateFrom($now);

        return $now->betweenIncluded($start, $end);
    }

    private function action(string $status, string $desired): string
    {
        $running = in_array($status, ['RUNNING', 'STARTING'], true);
        if ($desired === 'RUNNING' && ! $running) {
            return 'start';
        }
        if ($desired === 'STOPPED' && $running) {
            return 'stop';
        }

        return 'none';
    }
}
