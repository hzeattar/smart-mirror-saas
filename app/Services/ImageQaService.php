<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;

class ImageQaService
{
    public function fromUpload(?UploadedFile $file, string $kind): array
    {
        if (! $file) {
            return ['status' => 'missing', 'issues' => ['missing_file']];
        }

        return $this->fromBytes((string) file_get_contents($file->getRealPath()), $kind);
    }

    public function fromBytes(string $bytes, string $kind): array
    {
        if ($bytes === '') {
            return ['status' => 'missing', 'issues' => ['missing_file']];
        }

        $issues = [];
        $size = @getimagesizefromstring($bytes);
        $width = (int) ($size[0] ?? 0);
        $height = (int) ($size[1] ?? 0);
        $aspect = $height > 0 ? round($width / $height, 3) : 0.0;

        if ($width < 600 || $height < 600) {
            $issues[] = 'resolution_below_600px';
        }
        if ($aspect < 0.35 || $aspect > 2.2) {
            $issues[] = 'extreme_aspect_ratio';
        }

        $alphaCoverage = null;
        if ($kind === 'texture') {
            $alphaCoverage = $this->alphaCoverage($bytes);
            if ($alphaCoverage !== null && $alphaCoverage < 0.02) {
                $issues[] = 'no_transparent_cutout_detected';
            }
            if ($alphaCoverage !== null && $alphaCoverage > 0.85) {
                $issues[] = 'texture_mostly_transparent';
            }
        }

        $status = 'ok';
        if ($issues !== []) {
            $status = $kind === 'texture' && in_array('no_transparent_cutout_detected', $issues, true) ? 'failed' : 'warning';
        }

        return [
            'status' => $status,
            'width' => $width,
            'height' => $height,
            'aspect_ratio' => $aspect,
            'alpha_coverage' => $alphaCoverage,
            'issues' => $issues,
            'checked_at' => now()->toIso8601String(),
        ];
    }

    private function alphaCoverage(string $bytes): ?float
    {
        if (! function_exists('imagecreatefromstring')) {
            return null;
        }

        $image = @imagecreatefromstring($bytes);
        if ($image === false) {
            return null;
        }

        $width = imagesx($image);
        $height = imagesy($image);
        $transparent = 0;
        $samples = 0;
        $stepX = max(1, (int) floor($width / 32));
        $stepY = max(1, (int) floor($height / 32));

        for ($y = 0; $y < $height; $y += $stepY) {
            for ($x = 0; $x < $width; $x += $stepX) {
                $rgba = imagecolorat($image, $x, $y);
                $alpha = ($rgba & 0x7F000000) >> 24;
                if ($alpha > 8) {
                    $transparent++;
                }
                $samples++;
            }
        }
        imagedestroy($image);

        return $samples > 0 ? round($transparent / $samples, 4) : null;
    }
}
