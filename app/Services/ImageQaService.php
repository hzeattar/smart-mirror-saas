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

        $opaqueCoverage = null;
        $transparentCoverage = null;
        $contentCoverage = null;
        $edgeTouchRatio = null;
        if ($kind === 'texture') {
            $alpha = $this->alphaMetrics($bytes);
            $opaqueCoverage = $alpha['opaque_coverage'] ?? null;
            $transparentCoverage = $alpha['transparent_coverage'] ?? null;
            $contentCoverage = $alpha['content_coverage'] ?? null;
            $edgeTouchRatio = $alpha['edge_touch_ratio'] ?? null;
            if ($transparentCoverage !== null && $transparentCoverage < 0.02) {
                $issues[] = 'no_transparent_cutout_detected';
            }
            if ($opaqueCoverage !== null && $opaqueCoverage < 0.08) {
                $issues[] = 'texture_mostly_transparent';
            }
            if ($contentCoverage !== null && $contentCoverage < 0.30) {
                $issues[] = 'garment_too_small_in_frame';
            }
            if ($edgeTouchRatio !== null && $edgeTouchRatio > 0.25) {
                $issues[] = 'garment_touches_frame_edge';
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
            // Kept as a compatibility alias. It now explicitly means opaque foreground.
            'alpha_coverage' => $opaqueCoverage,
            'opaque_coverage' => $opaqueCoverage,
            'transparent_coverage' => $transparentCoverage,
            'content_coverage' => $contentCoverage,
            'edge_touch_ratio' => $edgeTouchRatio,
            'issues' => $issues,
            'checked_at' => now()->toIso8601String(),
        ];
    }

    private function alphaMetrics(string $bytes): array
    {
        if (! function_exists('imagecreatefromstring')) {
            return [];
        }

        $image = @imagecreatefromstring($bytes);
        if ($image === false) {
            return [];
        }

        $width = imagesx($image);
        $height = imagesy($image);
        $opaque = 0;
        $samples = 0;
        $minX = $width;
        $minY = $height;
        $maxX = -1;
        $maxY = -1;
        $edgeOpaque = 0;
        $edgeSamples = 0;
        $stepX = max(1, (int) floor($width / 32));
        $stepY = max(1, (int) floor($height / 32));

        for ($y = 0; $y < $height; $y += $stepY) {
            for ($x = 0; $x < $width; $x += $stepX) {
                $rgba = imagecolorat($image, $x, $y);
                $alpha = ($rgba & 0x7F000000) >> 24;
                if ($alpha <= 118) {
                    $opaque++;
                    $minX = min($minX, $x);
                    $minY = min($minY, $y);
                    $maxX = max($maxX, $x);
                    $maxY = max($maxY, $y);
                }
                if ($x < $stepX || $y < $stepY || $x >= $width - $stepX || $y >= $height - $stepY) {
                    $edgeSamples++;
                    if ($alpha <= 118) {
                        $edgeOpaque++;
                    }
                }
                $samples++;
            }
        }
        imagedestroy($image);

        if ($samples === 0) {
            return [];
        }

        $opaqueCoverage = round($opaque / $samples, 4);
        $bboxArea = $maxX >= $minX && $maxY >= $minY
            ? (($maxX - $minX + $stepX) * ($maxY - $minY + $stepY)) / max(1, $width * $height)
            : 0.0;

        return [
            'opaque_coverage' => $opaqueCoverage,
            'transparent_coverage' => round(1 - $opaqueCoverage, 4),
            'content_coverage' => round(min(1, $bboxArea), 4),
            'edge_touch_ratio' => $edgeSamples > 0 ? round($edgeOpaque / $edgeSamples, 4) : 0.0,
        ];
    }
}
