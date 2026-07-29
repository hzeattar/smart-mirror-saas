<?php

namespace Database\Seeders;

use App\Models\Product;
use Illuminate\Database\Seeder;

class DemoGarmentFitMetadataSeeder extends Seeder
{
    public function run(): void
    {
        $catalog = [
            'TSHIRT-001' => [
                'asset' => '/demo-garments/real-mint-tshirt.webp',
                'garment_type' => 'tshirt',
                'fit_profile' => [
                    'shoulder_expand' => 0.10,
                    'top_offset_ratio' => 0.06,
                    'height_ratio' => 1.28,
                    'forearm_occlusion' => true,
                ],
                'texture_anchor' => ['left' => 0, 'right' => 0, 'top' => 0, 'bottom' => 0],
                'sizes' => [
                    'S' => [42, 48, 45, 48, 21, 4, 66],
                    'M' => [44, 51, 48, 51, 22, 4, 69],
                    'L' => [46, 54, 51, 54, 23, 5, 72],
                ],
            ],
            'HOODIE-001' => [
                'asset' => '/demo-garments/real-navy-hoodie.webp',
                'garment_type' => 'hoodie',
                'fit_profile' => [
                    'shoulder_expand' => 0.17,
                    'top_offset_ratio' => 0.04,
                    'height_ratio' => 1.38,
                    'forearm_occlusion' => false,
                ],
                'texture_anchor' => ['left' => 0, 'right' => 0, 'top' => 0, 'bottom' => 0],
                'sizes' => [
                    'M' => [45, 55, 52, 55, 63, 7, 70],
                    'L' => [47, 58, 55, 58, 65, 7, 73],
                    'XL' => [49, 61, 58, 61, 67, 8, 76],
                ],
            ],
            'POLO-001' => [
                'asset' => '/demo-garments/real-coral-polo.webp',
                'garment_type' => 'polo',
                'fit_profile' => [
                    'shoulder_expand' => 0.09,
                    'top_offset_ratio' => 0.055,
                    'height_ratio' => 1.27,
                    'forearm_occlusion' => true,
                ],
                'texture_anchor' => ['left' => 0, 'right' => 0, 'top' => 0, 'bottom' => 0],
                'sizes' => [
                    'S' => [41, 47, 44, 47, 20, 3, 65],
                    'M' => [43, 50, 47, 50, 21, 4, 68],
                    'L' => [45, 53, 50, 53, 22, 4, 71],
                ],
            ],
        ];

        foreach ($catalog as $sku => $metadata) {
            $product = Product::query()->where('sku', $sku)->first();
            if (! $product) {
                continue;
            }

            $product->update([
                'garment_type' => $metadata['garment_type'],
                'fit_profile' => $metadata['fit_profile'],
                'texture_anchor' => $metadata['texture_anchor'],
                'base_image_url' => $metadata['asset'],
                'texture_image_url' => $metadata['asset'],
            ]);

            foreach ($metadata['sizes'] as $label => $values) {
                [$shoulder, $chest, $waist, $hip, $sleeve, $ease, $height] = $values;
                $product->sizingCharts()->updateOrCreate(
                    ['size_label' => $label],
                    [
                        'shoulder_width_cm' => $shoulder,
                        'chest_width_cm' => $chest,
                        'waist_width_cm' => $waist,
                        'hip_width_cm' => $hip,
                        'sleeve_length_cm' => $sleeve,
                        'fit_ease_cm' => $ease,
                        'height_cm' => $height,
                    ]
                );
            }
        }
    }
}
