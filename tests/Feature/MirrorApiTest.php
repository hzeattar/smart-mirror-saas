<?php

namespace Tests\Feature;

use App\Enums\CategoryStatus;
use App\Enums\LiveRestyleStatus;
use App\Enums\MirrorStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Category;
use App\Models\LiveRestyleSession;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\Tenant;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Config;
use Illuminate\Support\Str;
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

    public function test_live_restyle_config_is_blocked_by_default_and_never_returns_secrets(): void
    {
        Config::set('live_restyle.enabled', false);
        Config::set('live_restyle.model', 'decart/lucy2-vton/realtime');

        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'live-config.test', 'status' => TenantStatus::Active]);
        $mirror = Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => 'LIVE1234',
            'location_name' => 'Pilot Room',
            'status' => MirrorStatus::Pending,
            'metadata' => [
                'kiosk_profile' => [
                    'version' => 2,
                    'config' => ['live_restyle_enabled' => true],
                ],
            ],
        ]);

        $token = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'LIVE1234', 'device_name' => 'Kiosk'])->assertOk()->json('token');
        $payload = $this->withToken($token)->getJson('/api/mirror/live-restyle-config')
            ->assertOk()
            ->assertJsonPath('live_restyle.enabled', false)
            ->assertJsonPath('live_restyle.blocked_reason', 'global_disabled')
            ->json();

        $this->assertStringNotContainsString('key', strtolower(json_encode($payload)));
        $this->assertDatabaseMissing('live_restyle_sessions', ['mirror_id' => $mirror->id]);
    }

    public function test_mirror_can_create_and_finish_capped_live_restyle_session(): void
    {
        Config::set('live_restyle.enabled', true);
        Config::set('live_restyle.max_seconds', 20);
        Config::set('live_restyle.daily_seconds_limit', 120);
        Config::set('live_restyle.price_per_second_usd', 0.02);

        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'live-session.test', 'status' => TenantStatus::Active]);
        Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => 'LIVE5678',
            'location_name' => 'Pilot Room',
            'status' => MirrorStatus::Pending,
            'metadata' => [
                'kiosk_profile' => [
                    'version' => 3,
                    'config' => ['live_restyle_enabled' => true],
                ],
            ],
        ]);

        $token = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'LIVE5678', 'device_name' => 'Kiosk'])->assertOk()->json('token');
        $sessionId = $this->withToken($token)->postJson('/api/mirror/live-restyle-sessions', [
            'reference_image_url' => 'https://example.test/product.png',
            'prompt' => 'commercial fitting-room restyle',
            'max_seconds' => 20,
        ])->assertCreated()
            ->assertJsonPath('session.status', 'active')
            ->assertJsonPath('session.max_seconds', 20)
            ->json('session.id');

        $this->withToken($token)->patchJson('/api/mirror/live-restyle-sessions/'.$sessionId, [
            'status' => 'completed',
            'duration_seconds' => 20,
        ])->assertOk()
            ->assertJsonPath('session.status', 'completed')
            ->assertJsonPath('session.duration_seconds', 20)
            ->assertJsonPath('session.estimated_cost_usd', 0.4);
    }

    public function test_live_restyle_session_is_tenant_isolated(): void
    {
        Config::set('live_restyle.enabled', true);

        $tenantA = Tenant::query()->create(['name' => 'A', 'domain' => 'a-live.test', 'status' => TenantStatus::Active]);
        $tenantB = Tenant::query()->create(['name' => 'B', 'domain' => 'b-live.test', 'status' => TenantStatus::Active]);
        $mirrorA = Mirror::query()->create([
            'tenant_id' => $tenantA->id,
            'pairing_code' => 'LIVA1111',
            'location_name' => 'A',
            'status' => MirrorStatus::Pending,
            'metadata' => ['kiosk_profile' => ['version' => 1, 'config' => ['live_restyle_enabled' => true]]],
        ]);
        Mirror::query()->create([
            'tenant_id' => $tenantB->id,
            'pairing_code' => 'LIVB2222',
            'location_name' => 'B',
            'status' => MirrorStatus::Pending,
            'metadata' => ['kiosk_profile' => ['version' => 1, 'config' => ['live_restyle_enabled' => true]]],
        ]);

        $tokenB = $this->postJson('/api/mirrors/pair', ['pairing_code' => 'LIVB2222', 'device_name' => 'Kiosk B'])->assertOk()->json('token');
        $session = LiveRestyleSession::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $tenantA->id,
            'mirror_id' => $mirrorA->id,
            'provider' => 'fal',
            'model' => 'decart/lucy2-vton/realtime',
            'status' => LiveRestyleStatus::Active,
            'max_seconds' => 20,
            'started_at' => now(),
        ]);

        $this->withToken($tokenB)->patchJson('/api/mirror/live-restyle-sessions/'.$session->public_id, [
            'status' => 'cancelled',
            'duration_seconds' => 1,
        ])->assertNotFound();
    }
}
