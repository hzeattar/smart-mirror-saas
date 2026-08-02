<?php

namespace Tests\Feature;

use App\Enums\CategoryStatus;
use App\Enums\MirrorStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Category;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\Tenant;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class MirrorApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_mirror_can_pair_and_fetch_only_its_tenant_catalog(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'store.test', 'status' => TenantStatus::Active]);
        $mirror = Mirror::query()->create(['tenant_id' => $tenant->id, 'pairing_code' => 'PAIR1234', 'location_name' => 'Front', 'status' => MirrorStatus::Pending]);
        $category = Category::query()->create(['tenant_id' => $tenant->id, 'name' => 'Tops', 'slug' => 'tops', 'status' => CategoryStatus::Active]);
        $product = Product::query()->create([
            'tenant_id' => $tenant->id,
            'category_id' => $category->id,
            'name' => 'Shirt',
            'unit_price' => 500,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
            'base_image_url' => '/demo-garments/real/shirt-front.png',
            'texture_image_url' => '/demo-garments/real/shirt-texture.png',
            'image_qa' => ['base' => ['status' => 'ok'], 'texture' => ['status' => 'ok']],
        ]);
        foreach (['S', 'M', 'L', 'XL'] as $label) {
            $product->sizingCharts()->create(['size_label' => $label, 'shoulder_width_cm' => 44, 'chest_width_cm' => 50, 'height_cm' => 68]);
        }
        Product::query()->create([
            'tenant_id' => $tenant->id,
            'category_id' => $category->id,
            'name' => 'Incomplete Shirt',
            'unit_price' => 300,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
        ]);

        $token = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'PAIR1234', 'device_name' => 'Kiosk'])->assertOk()->json('token');
        $this->withToken($token)->getJson('/api/mirror/catalog')
            ->assertOk()
            ->assertJsonPath('products.0.name', 'Shirt')
            ->assertJsonPath('products.0.readiness.mirror_catalog_ready', true)
            ->assertJsonCount(4, 'products.0.sizes')
            ->assertJsonCount(1, 'products');

        $this->withToken($token)->getJson('/api/mirror/kiosk-config')
            ->assertOk()
            ->assertJsonPath('profile_version', 1)
            ->assertJsonPath('config.outfit_count', 3)
            ->assertJsonPath('config.gestures.hold_seconds', 0.75);
    }

    public function test_admin_updates_mirror_kiosk_profile_for_same_tenant(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'profile.test', 'status' => TenantStatus::Active]);
        $mirror = Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => 'CFG12345',
            'location_name' => 'Pilot Room',
            'status' => MirrorStatus::Pending,
        ]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Admin',
            'email' => 'profile@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        Sanctum::actingAs($user, ['admin']);

        $this->patchJson('/api/admin/mirrors/'.$mirror->id.'/kiosk-config', [
            'config' => [
                'outfit_count' => 5,
                'pose_every_n' => 3,
                'kiosk_health_hud' => false,
                'gestures' => ['hold_seconds' => 0.6, 'swipe_distance' => 0.16],
            ],
        ])->assertOk()
            ->assertJsonPath('mirror.kiosk_profile.version', 2)
            ->assertJsonPath('mirror.kiosk_profile.config.outfit_count', 5)
            ->assertJsonPath('mirror.kiosk_profile.config.gestures.hold_seconds', 0.6);

        $token = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'CFG12345', 'device_name' => 'Kiosk'])->assertOk()->json('token');
        $this->withToken($token)->getJson('/api/mirror/kiosk-config')
            ->assertOk()
            ->assertJsonPath('profile_version', 2)
            ->assertJsonPath('config.pose_every_n', 3)
            ->assertJsonPath('config.kiosk_health_hud', false);
    }
}
