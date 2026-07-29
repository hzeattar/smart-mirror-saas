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
        ];

        Product::query()
            ->where('tenant_id', $tenant->id)
            ->whereIn('sku', ['TSHIRT-001', 'HOODIE-001', 'POLO-001'])
            ->update(['status' => ProductStatus::Inactive->value]);

        $products = [
            [
                'sku' => 'PHOTO-TSHIRT-001',
                'category' => 'tops',
                'name' => 'Essential White V-Neck T-Shirt',
                'description' => 'Photographic demo asset. Source: Wikimedia Commons, White-tshirt.jpg, CC0.',
                'garment_type' => 'tshirt',
                'price' => 699,
                'url' => 'https://commons.wikimedia.org/wiki/Special:Redirect/file/White-tshirt.jpg',
                'fit_profile' => [
                    'shoulder_expand' => 0.08,
                    'top_offset_ratio' => 0.06,
                    'height_ratio' => 1.24,
                    'forearm_occlusion' => true,
                ],
            ],
            [
                'sku' => 'PHOTO-SHIRT-001',
                'category' => 'tops',
                'name' => 'Classic Blue Business Shirt',
                'description' => 'Photographic demo asset. Source: Wikimedia Commons, Blue Business Shirt.jpg, CC BY-SA 3.0.',
                'garment_type' => 'shirt',
                'price' => 1099,
                'url' => 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Blue_Business_Shirt.jpg',
                'fit_profile' => [
                    'shoulder_expand' => 0.10,
                    'top_offset_ratio' => 0.05,
                    'height_ratio' => 1.34,
                    'forearm_occlusion' => true,
                ],
            ],
            [
                'sku' => 'PHOTO-JACKET-001',
                'category' => 'outerwear',
                'name' => 'Classic Denim Jacket',
                'description' => 'Photographic demo asset. Source: Wikimedia Commons, Jean jacket.jpg, CC0.',
                'garment_type' => 'jacket',
                'price' => 1599,
                'url' => 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Jean_jacket.jpg',
                'fit_profile' => [
                    'shoulder_expand' => 0.15,
                    'top_offset_ratio' => 0.04,
                    'height_ratio' => 1.32,
                    'forearm_occlusion' => true,
                ],
            ],
            [
                'sku' => 'PHOTO-TROUSER-001',
                'category' => 'trousers',
                'name' => 'Khaki Straight-Leg Trousers',
                'description' => 'Photographic demo asset. Source: Wikimedia Commons, Trousers-colourisolated.jpg, CC BY-SA 2.0.',
                'garment_type' => 'trousers',
                'price' => 1199,
                'url' => 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Trousers-colourisolated.jpg',
                'fit_profile' => [
                    'waist_expand' => 0.06,
                    'height_ratio' => 2.20,
                    'forearm_occlusion' => false,
                ],
            ],
            [
                'sku' => 'PHOTO-SUIT-001',
                'category' => 'suits',
                'name' => 'Tailored Navy Suit Jacket',
                'description' => "Photographic demo asset. Source: Wikimedia Commons, Man's suit jacket.jpg, CC BY 2.0.",
                'garment_type' => 'suit',
                'price' => 2499,
                'url' => 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Man%27s_suit_jacket.jpg',
                'fit_profile' => [
                    'shoulder_expand' => 0.13,
                    'top_offset_ratio' => 0.04,
                    'height_ratio' => 1.42,
                    'forearm_occlusion' => true,
                ],
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
                    'base_image_url' => $item['url'],
                    'texture_image_url' => $item['url'],
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
                ['size_label' => 'S', 'waist_width_cm' => 38, 'hip_width_cm' => 48, 'height_cm' => 100, 'fit_ease_cm' => 2, 'sort_order' => 0],
                ['size_label' => 'M', 'waist_width_cm' => 41, 'hip_width_cm' => 51, 'height_cm' => 102, 'fit_ease_cm' => 2, 'sort_order' => 1],
                ['size_label' => 'L', 'waist_width_cm' => 44, 'hip_width_cm' => 54, 'height_cm' => 104, 'fit_ease_cm' => 3, 'sort_order' => 2],
                ['size_label' => 'XL', 'waist_width_cm' => 47, 'hip_width_cm' => 57, 'height_cm' => 106, 'fit_ease_cm' => 3, 'sort_order' => 3],
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
