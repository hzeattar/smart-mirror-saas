<?php

namespace App\Http\Controllers;

use App\Enums\TryOnJobStatus;
use App\Models\TryOnJob;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Storage;

class TryOnResultController extends Controller
{
    public function __invoke(TryOnJob $job): Response
    {
        abort_unless($job->status === TryOnJobStatus::Completed && $job->result_image_path, 404);
        abort_if($job->expires_at && $job->expires_at->isPast(), 410);

        $disk = Storage::disk(config('filesystems.default'));
        abort_unless($disk->exists($job->result_image_path), 404);

        return response($disk->get($job->result_image_path), 200, [
            'Content-Type' => $disk->mimeType($job->result_image_path) ?: 'image/jpeg',
            'Cache-Control' => 'private, max-age=300',
        ]);
    }
}
