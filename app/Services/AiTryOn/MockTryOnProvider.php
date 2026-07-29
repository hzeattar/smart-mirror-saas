<?php

namespace App\Services\AiTryOn;

use App\Models\Product;
use App\Models\TryOnJob;

class MockTryOnProvider implements AiTryOnProvider
{
    public function generate(TryOnJob $job, Product $product, string $personImage, ?string $garmentImage): TryOnResult
    {
        if (function_exists('imagecreatefromstring')) {
            $image = @imagecreatefromstring($personImage);
            if ($image !== false) {
                $width = imagesx($image);
                $height = imagesy($image);
                $bannerHeight = max(52, (int) round($height * 0.10));
                $black = imagecolorallocatealpha($image, 5, 17, 28, 24);
                $accent = imagecolorallocate($image, 88, 224, 181);
                imagefilledrectangle($image, 0, $height - $bannerHeight, $width, $height, $black);
                imagestring($image, 5, 22, $height - $bannerHeight + 16, 'AI MOCK TRY-ON: '.$product->name, $accent);

                ob_start();
                imagejpeg($image, null, 88);
                $bytes = (string) ob_get_clean();
                imagedestroy($image);

                return new TryOnResult($bytes);
            }
        }

        return new TryOnResult($personImage);
    }
}
