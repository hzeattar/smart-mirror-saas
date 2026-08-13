<?php

namespace Tests\Feature;

use App\Enums\TenantStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Tenant;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class ProductMeasurementContractTest extends TestCase
{
    use RefreshDatabase;

    private function actingAdmin(): void
    {
        $tenant = Tenant::query()->create(['name' => 'Fit Store', 'domain' => 'fit.test', 'status' => TenantStatus::Active]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Admin',
            'email' => 'fit@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        Sanctum::actingAs($user, ['admin']);
    }

    public function test_trousers_require_flat_waist_hip_length_and_inseam(): void
    {
        $this->actingAdmin();
        $this->postJson('/api/admin/products', [
            'name' => 'Depth Trousers',
            'garment_type' => 'trousers',
            'unit_price' => 900,
            'currency' => 'EGP',
            'sizes' => [[
                'size_label' => 'M',
                'waist_width_cm' => 44,
                'hip_width_cm' => 52,
                'height_cm' => 104,
            ]],
        ])->assertUnprocessable()->assertJsonValidationErrors('sizes.0.inseam_length_cm');
    }

    public function test_shirt_contract_persists_schema_basis_and_fit_readiness(): void
    {
        $this->actingAdmin();
        $response = $this->postJson('/api/admin/products', [
            'name' => 'Measured Shirt',
            'garment_type' => 'shirt',
            'unit_price' => 1000,
            'currency' => 'EGP',
            'sizes' => [[
                'size_label' => 'M',
                'shoulder_width_cm' => 44,
                'chest_width_cm' => 52,
                'sleeve_length_cm' => 62,
                'height_cm' => 70,
            ]],
        ])->assertCreated();

        $response->assertJsonPath('product.measurement_schema_version', 1)
            ->assertJsonPath('product.measurement_basis', 'flat_garment')
            ->assertJsonPath('readiness.fit_ready', true)
            ->assertJsonPath('readiness.reasons', []);
    }

    public function test_active_product_cannot_drop_required_measurements_on_partial_update(): void
    {
        $this->actingAdmin();
        $productId = $this->postJson('/api/admin/products', [
            'name' => 'Complete Trousers',
            'garment_type' => 'trousers',
            'unit_price' => 1000,
            'currency' => 'EGP',
            'status' => 'active',
            'sizes' => [[
                'size_label' => 'M',
                'waist_width_cm' => 44,
                'hip_width_cm' => 52,
                'inseam_length_cm' => 78,
                'height_cm' => 104,
            ]],
        ])->assertCreated()->json('product.id');

        $this->putJson("/api/admin/products/$productId", [
            'sizes' => [[
                'size_label' => 'M',
                'waist_width_cm' => 44,
                'hip_width_cm' => 52,
                'height_cm' => 104,
            ]],
        ])->assertUnprocessable()->assertJsonValidationErrors('sizes.0.inseam_length_cm');
    }
}
