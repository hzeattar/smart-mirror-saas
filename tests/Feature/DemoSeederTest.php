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
            ->where('sku', 'like', 'PHOTO-%')
            ->with('sizingCharts')
            ->get();

        $this->assertCount(5, $products);

        foreach ($products as $product) {
            $this->assertCount(4, $product->sizingCharts);

            foreach ($product->sizingCharts as $size) {
                $this->assertNotNull($size->shoulder_width_cm);
                $this->assertNotNull($size->chest_width_cm);
                $this->assertNotNull($size->height_cm);
            }
        }
    }
}
