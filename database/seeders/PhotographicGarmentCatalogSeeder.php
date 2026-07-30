<?php

namespace Database\Seeders;

use App\Enums\BackgroundRemovalStatus;
use App\Enums\CategoryStatus;
use App\Enums\ProductStatus;
use App\Models\Category;
use App\Models\Product;
use App\Models\Tenant;
use Illuminate\Database\Seeder;

class PhotographicGarmentCatalogSeeder extends Seeder
{
    public function run(): void
    {
        $tenant = Tenant::query()->firstOrFail();

        $categories = [
            'tops' => Category::query()->firstOrCreate(
                ['tenant_id' => $tenant->id, 'slug' => 'tops'],
                ['name' => 'T-Shirts & Shirts', 'status' => CategoryStatus::Active]
            ),
            'outerwear' => Category::query()->firstOrCreate(
                ['tenant_id' => $tenant->id, 'slug' => 'outerwear'],
                ['name' => 'Jackets & Hoodies', 'status' => CategoryStatus::Active]
            ),
            'trousers' => Category::query()->firstOrCreate(
                ['tenant_id' => $tenant->id, 'slug' => 'trousers'],
                ['name' => 'Trousers', 'status' => CategoryStatus::Active]
            ),
            'suits' => Category::query()->firstOrCreate(
                ['tenant_id' => $tenant->id, 'slug' => 'suits'],
                ['name' => 'Suits', 'status' => CategoryStatus::Active]
            ),
            'dresses' => Category::query()->firstOrCreate(
                ['tenant_id' => $tenant->id, 'slug' => 'dresses'],
                ['name' => 'Dresses', 'status' => CategoryStatus::Active]
            ),
        ];

        Product::query()
            ->where('tenant_id', $tenant->id)
            ->where(function ($query): void {
                $query->whereIn('sku', ['TSHIRT-001', 'HOODIE-001', 'POLO-001'])
                    ->orWhere('sku', 'like', 'PHOTO-%');
            })
            ->delete();

        $products = [
            [
                'sku' => 'REAL-SHIRT-001',
                'category' => 'tops',
                'name' => 'White Oxford Shirt',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'shirt',
                'price' => 1199,
                'local_asset' => '/demo-garments/real/real-white-oxford-shirt.webp',
                'fit_profile' => ['shoulder_expand' => 0.10, 'top_offset_ratio' => 0.05, 'height_ratio' => 1.34, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-TSHIRT-001',
                'category' => 'tops',
                'name' => 'Black V-Neck T-Shirt',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'tshirt',
                'price' => 699,
                'local_asset' => '/demo-garments/real/real-black-vneck-tshirt.webp',
                'fit_profile' => ['shoulder_expand' => 0.08, 'top_offset_ratio' => 0.06, 'height_ratio' => 1.24, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-SHIRT-002',
                'category' => 'tops',
                'name' => 'Sage Linen Shirt',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'shirt',
                'price' => 999,
                'local_asset' => '/demo-garments/real/real-sage-linen-shirt.webp',
                'fit_profile' => ['shoulder_expand' => 0.09, 'top_offset_ratio' => 0.05, 'height_ratio' => 1.32, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-JACKET-001',
                'category' => 'outerwear',
                'name' => 'Classic Denim Jacket',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'jacket',
                'price' => 1599,
                'local_asset' => '/demo-garments/real/real-denim-jacket.webp',
                'fit_profile' => ['shoulder_expand' => 0.15, 'top_offset_ratio' => 0.04, 'height_ratio' => 1.32, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-HOODIE-001',
                'category' => 'outerwear',
                'name' => 'Charcoal Everyday Hoodie',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'hoodie',
                'price' => 1399,
                'local_asset' => '/demo-garments/real/real-charcoal-hoodie.webp',
                'fit_profile' => ['shoulder_expand' => 0.14, 'top_offset_ratio' => 0.04, 'height_ratio' => 1.36, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-TROUSER-001',
                'category' => 'trousers',
                'name' => 'Khaki Straight-Leg Chinos',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'trousers',
                'price' => 1199,
                'local_asset' => '/demo-garments/real/real-khaki-chinos.webp',
                'fit_profile' => ['waist_expand' => 0.06, 'height_ratio' => 2.20, 'forearm_occlusion' => false],
            ],
            [
                'sku' => 'REAL-TROUSER-002',
                'category' => 'trousers',
                'name' => 'Black Tailored Trousers',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'trousers',
                'price' => 1299,
                'local_asset' => '/demo-garments/real/real-black-tailored-trousers.webp',
                'fit_profile' => ['waist_expand' => 0.05, 'height_ratio' => 2.18, 'forearm_occlusion' => false],
            ],
            [
                'sku' => 'REAL-SUIT-001',
                'category' => 'suits',
                'name' => 'Tailored Navy Suit Jacket',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'suit',
                'price' => 2499,
                'local_asset' => '/demo-garments/real/real-navy-suit-jacket.webp',
                'fit_profile' => ['shoulder_expand' => 0.13, 'top_offset_ratio' => 0.04, 'height_ratio' => 1.42, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-SUIT-002',
                'category' => 'suits',
                'name' => 'Grey Two-Piece Suit',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'suit',
                'price' => 2799,
                'local_asset' => '/demo-garments/real/real-grey-two-piece-suit.webp',
                'fit_profile' => ['shoulder_expand' => 0.14, 'top_offset_ratio' => 0.04, 'height_ratio' => 1.44, 'forearm_occlusion' => true],
            ],
            [
                'sku' => 'REAL-DRESS-001',
                'category' => 'dresses',
                'name' => 'Burgundy Midi Dress',
                'description' => 'Local realistic demo garment texture. Replace with store-owned photography before commercial use.',
                'garment_type' => 'dress',
                'price' => 1899,
                'local_asset' => '/demo-garments/real/real-burgundy-midi-dress.webp',
                'fit_profile' => ['shoulder_expand' => 0.07, 'top_offset_ratio' => 0.06, 'height_ratio' => 1.95, 'forearm_occlusion' => true],
            ],
        ];

        foreach ($products as $index => $item) {
            $product = Product::query()->withTrashed()->updateOrCreate(
                ['tenant_id' => $tenant->id, 'sku' => $item['sku']],
                [
                    'category_id' => $categories[$item['category']]->id,
                    'name' => $item['name'],
                    'description' => $item['description'],
                    'garment_type' => $item['garment_type'],
                    'fit_profile' => $item['fit_profile'],
                    'texture_anchor' => ['left' => 0.02, 'right' => 0.02, 'top' => 0.02, 'bottom' => 0.02],
                    'base_image_url' => $item['local_asset'],
                    'texture_image_url' => $item['local_asset'],
                    'unit_price' => $item['price'],
                    'currency' => 'EGP',
                    'status' => ProductStatus::Active,
                    'background_removal_status' => BackgroundRemovalStatus::NotRequested,
                    'background_removal_error' => null,
                ]
            );

            if ($product->trashed()) {
                $product->restore();
            }

            $product->sizingCharts()->delete();
            $product->sizingCharts()->createMany($this->sizesFor($item['garment_type'], $index));
        }
    }

    private function sizesFor(string $garmentType, int $offset): array
    {
        if ($garmentType === 'trousers') {
            return [
                ['size_label' => 'S', 'shoulder_width_cm' => 38, 'chest_width_cm' => 48, 'waist_width_cm' => 38, 'hip_width_cm' => 48, 'height_cm' => 100, 'fit_ease_cm' => 2, 'sort_order' => 0],
                ['size_label' => 'M', 'shoulder_width_cm' => 41, 'chest_width_cm' => 51, 'waist_width_cm' => 41, 'hip_width_cm' => 51, 'height_cm' => 102, 'fit_ease_cm' => 2, 'sort_order' => 1],
                ['size_label' => 'L', 'shoulder_width_cm' => 44, 'chest_width_cm' => 54, 'waist_width_cm' => 44, 'hip_width_cm' => 54, 'height_cm' => 104, 'fit_ease_cm' => 3, 'sort_order' => 2],
                ['size_label' => 'XL', 'shoulder_width_cm' => 47, 'chest_width_cm' => 57, 'waist_width_cm' => 47, 'hip_width_cm' => 57, 'height_cm' => 106, 'fit_ease_cm' => 3, 'sort_order' => 3],
            ];
        }

        $extra = $garmentType === 'jacket' || $garmentType === 'suit' ? 2 : 0;

        return [
            ['size_label' => 'S', 'shoulder_width_cm' => 42 + $extra, 'chest_width_cm' => 48 + $extra, 'waist_width_cm' => 46 + $extra, 'hip_width_cm' => 48 + $extra, 'sleeve_length_cm' => 61 + $offset, 'height_cm' => 66 + $offset, 'fit_ease_cm' => 3 + $extra, 'sort_order' => 0],
            ['size_label' => 'M', 'shoulder_width_cm' => 44 + $extra, 'chest_width_cm' => 51 + $extra, 'waist_width_cm' => 49 + $extra, 'hip_width_cm' => 51 + $extra, 'sleeve_length_cm' => 63 + $offset, 'height_cm' => 69 + $offset, 'fit_ease_cm' => 4 + $extra, 'sort_order' => 1],
            ['size_label' => 'L', 'shoulder_width_cm' => 46 + $extra, 'chest_width_cm' => 54 + $extra, 'waist_width_cm' => 52 + $extra, 'hip_width_cm' => 54 + $extra, 'sleeve_length_cm' => 65 + $offset, 'height_cm' => 72 + $offset, 'fit_ease_cm' => 4 + $extra, 'sort_order' => 2],
            ['size_label' => 'XL', 'shoulder_width_cm' => 48 + $extra, 'chest_width_cm' => 57 + $extra, 'waist_width_cm' => 55 + $extra, 'hip_width_cm' => 57 + $extra, 'sleeve_length_cm' => 67 + $offset, 'height_cm' => 75 + $offset, 'fit_ease_cm' => 5 + $extra, 'sort_order' => 3],
        ];
    }
}
