<?php

namespace Tests\Feature;

use App\Enums\CategoryStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Category;
use App\Models\Product;
use App\Models\Tenant;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class ProductAssetPipelineTest extends TestCase
{
    use RefreshDatabase;

    public function test_admin_upload_records_asset_metadata_and_cutout_readiness(): void
    {
        Storage::fake('local');
        config(['filesystems.default' => 'local']);

        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'assets.test', 'status' => TenantStatus::Active]);
        $category = Category::query()->create(['tenant_id' => $tenant->id, 'name' => 'Tops', 'slug' => 'tops', 'status' => CategoryStatus::Active]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Admin',
            'email' => 'assets@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        Sanctum::actingAs($user, ['admin']);

        $payload = [
            'name' => 'Store White Shirt',
            'sku' => 'STORE-SHIRT-001',
            'category_id' => $category->id,
            'description' => 'Store-owned commercial product photo.',
            'garment_type' => 'shirt',
            'unit_price' => 1299,
            'currency' => 'EGP',
            'status' => 'active',
            'asset_source' => 'Store studio shoot 2026',
            'asset_license' => 'Store owned',
            'is_demo_asset' => false,
            'base_image' => UploadedFile::fake()->image('front.jpg', 900, 1200),
            'texture_image' => UploadedFile::fake()->image('texture.png', 900, 1200),
            'sizes' => collect(['S', 'M', 'L', 'XL'])->map(fn (string $label) => [
                'size_label' => $label,
                'shoulder_width_cm' => 44,
                'chest_width_cm' => 52,
                'height_cm' => 72,
            ])->all(),
        ];

        $response = $this->post('/api/admin/products', $payload, ['Accept' => 'application/json'])
            ->assertCreated()
            ->assertJsonPath('readiness.label', 'Needs Cutout');

        $this->assertFalse($response->json('product.is_demo_asset'));
        $this->assertSame('Store studio shoot 2026', $response->json('product.asset_source'));
        $this->assertContains('no_transparent_cutout_detected', $response->json('readiness.issues'));
    }

    public function test_admin_product_readiness_filters_use_catalog_gate(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'filters.test', 'status' => TenantStatus::Active]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Admin',
            'email' => 'filters@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        Sanctum::actingAs($user, ['admin']);

        $ready = Product::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Ready Shirt',
            'unit_price' => 1000,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
            'base_image_url' => '/demo-garments/real/ready-front.png',
            'texture_image_url' => '/demo-garments/real/ready-texture.png',
            'asset_source' => 'Store shoot',
            'asset_license' => 'Owned',
            'image_qa' => ['base' => ['status' => 'ok'], 'texture' => ['status' => 'ok']],
        ]);
        foreach (['S', 'M', 'L', 'XL'] as $label) {
            $ready->sizingCharts()->create(['size_label' => $label, 'shoulder_width_cm' => 44, 'chest_width_cm' => 52, 'height_cm' => 70]);
        }
        Product::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Missing Texture',
            'unit_price' => 800,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
            'base_image_url' => '/demo-garments/real/missing-front.png',
        ]);

        $this->getJson('/api/admin/products?readiness=production_ready')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.name', 'Ready Shirt');

        $this->getJson('/api/admin/products?readiness=needs_work')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.name', 'Missing Texture');
    }
}
