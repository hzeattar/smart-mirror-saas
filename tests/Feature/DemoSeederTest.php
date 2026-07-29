<?php

namespace Tests\Feature;

use App\Models\Product;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DemoSeederTest extends TestCase
{
    use RefreshDatabase;

    public function test_demo_seeders_create_photographic_catalog_with_complete_size_rows(): void
    {
        $this->seed();

        $products = Product::query()
            ->where('sku', 'like', 'REAL-%')
            ->with('sizingCharts')
            ->get();

        $this->assertCount(10, $products);
        $this->assertSame(0, Product::query()->where('sku', 'like', 'PHOTO-%')->where('status', 'active')->count());
        $this->assertSame(0, Product::query()->whereIn('sku', ['TSHIRT-001', 'HOODIE-001', 'POLO-001'])->where('status', 'active')->count());
        $this->assertCount(10, $products->pluck('texture_image_url')->unique());

        foreach ($products as $product) {
            $this->assertCount(4, $product->sizingCharts);
            $this->assertStringStartsWith('/demo-garments/real/', $product->base_image_url);
            $this->assertStringStartsWith('/demo-garments/real/', $product->texture_image_url);

            foreach ($product->sizingCharts as $size) {
                $this->assertNotNull($size->shoulder_width_cm);
                $this->assertNotNull($size->chest_width_cm);
                $this->assertNotNull($size->height_cm);
            }
        }

        $metadata = json_decode(file_get_contents(base_path('docs/REAL_GARMENT_SOURCES.json')), true);
        $this->assertGreaterThanOrEqual(10, count($metadata['assets'] ?? []));
    }
}
