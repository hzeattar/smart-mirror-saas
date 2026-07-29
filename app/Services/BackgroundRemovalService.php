<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Facades\Storage;
use RuntimeException;

class BackgroundRemovalService
{
    public function remove(string $inputPath, string $outputPath): void
    {
        $disk = Storage::disk(config('filesystems.default'));
        $inputBytes = $disk->get($inputPath);
        $endpoint = config('garment_processing.endpoint');

        if ($endpoint) {
            $response = Http::timeout(120)
                ->withToken((string) config('garment_processing.api_token'))
                ->attach('image', $inputBytes, basename($inputPath))
                ->post($endpoint);
            if (! $response->successful()) {
                throw new RuntimeException('Background removal API failed: '.$response->status());
            }
            $disk->put($outputPath, $response->body());

            return;
        }

        $tempInput = tempnam(sys_get_temp_dir(), 'garment-in-');
        $tempOutput = $tempInput.'.png';
        file_put_contents($tempInput, $inputBytes);

        $result = Process::timeout(150)->run([
            config('garment_processing.python_binary', 'python3'),
            base_path('cv_client/tools/remove_background.py'),
            $tempInput,
            $tempOutput,
        ]);

        if ($result->failed() || ! file_exists($tempOutput)) {
            @unlink($tempInput);
            throw new RuntimeException('Local background removal failed: '.$result->errorOutput());
        }

        $disk->put($outputPath, file_get_contents($tempOutput));
        @unlink($tempInput);
        @unlink($tempOutput);
    }
}
