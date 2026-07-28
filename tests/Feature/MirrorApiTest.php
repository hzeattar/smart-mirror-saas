<?php

namespace Tests\Feature;

use App\Enums\CategoryStatus;
use App\Enums\MirrorStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Models\Category;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\Tenant;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MirrorApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_mirror_can_pair_and_fetch_only_its_tenant_catalog(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'store.test', 'status' => TenantStatus::Active]);
        $mirror = Mirror::query()->create(['tenant_id' => $tenant->id, 'pairing_code' => 'PAIR1234', 'location_name' => 'Front', 'status' => MirrorStatus::Pending]);
        $category = Category::query()->create(['tenant_id' => $tenant->id, 'name' => 'Tops', 'slug' => 'tops', 'status' => CategoryStatus::Active]);
        $product = Product::query()->create(['tenant_id' => $tenant->id, 'category_id' => $category->id, 'name' => 'Shirt', 'unit_price' => 500, 'currency' => 'EGP', 'status' => ProductStatus::Active]);
        $product->sizingCharts()->create(['size_label' => 'M', 'shoulder_width_cm' => 44, 'chest_width_cm' => 50, 'height_cm' => 68]);

        $token = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'PAIR1234', 'device_name' => 'Kiosk'])->assertOk()->json('token');
        $this->withToken($token)->getJson('/api/mirror/catalog')
            ->assertOk()->assertJsonPath('products.0.name', 'Shirt')->assertJsonCount(1, 'products.0.sizes');
    }
}
