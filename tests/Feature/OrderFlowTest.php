<?php

namespace Tests\Feature;

use App\Enums\MirrorStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\Tenant;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Tests\TestCase;

class OrderFlowTest extends TestCase
{
    use RefreshDatabase;

    public function test_mirror_creates_checkout_and_customer_submits_order(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => 'order.test', 'status' => TenantStatus::Active]);
        $plain = Str::random(64);
        $mirror = Mirror::query()->create(['tenant_id' => $tenant->id, 'pairing_code' => 'ORDER123', 'api_token_hash' => hash('sha256', $plain), 'location_name' => 'Room 1', 'status' => MirrorStatus::Paired]);
        $product = Product::query()->create(['tenant_id' => $tenant->id, 'name' => 'Jacket', 'unit_price' => 1200, 'currency' => 'EGP', 'status' => ProductStatus::Active]);
        $size = $product->sizingCharts()->create(['size_label' => 'L', 'shoulder_width_cm' => 46, 'chest_width_cm' => 54, 'height_cm' => 72]);

        $session = $this->withToken($plain)->postJson('/api/mirror/checkout-sessions', [
            'type' => 'in_store',
            'items' => [['product_id' => $product->id, 'sizing_chart_id' => $size->id, 'quantity' => 1]],
        ])->assertCreated();

        $token = $session->json('token');
        $this->postJson('/api/checkout/'.$token.'/orders', [
            'type' => 'in_store', 'customer_name' => 'Customer', 'customer_phone' => '01000000000',
            'items' => [['product_id' => $product->id, 'quantity' => 1]],
        ])->assertCreated()->assertJsonPath('order.total', 1200);

        $this->assertDatabaseHas('orders', ['tenant_id' => $tenant->id, 'mirror_id' => $mirror->id, 'total' => 1200]);
    }
}
