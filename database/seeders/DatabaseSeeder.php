<?php

namespace Database\Seeders;

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
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        $tenant = Tenant::query()->firstOrCreate(
            ['domain' => env('DEMO_TENANT_DOMAIN', 'demo.smartmirror.local')],
            ['name' => env('DEMO_TENANT_NAME', 'Demo Fashion Store'), 'status' => TenantStatus::Active]
        );

        User::query()->updateOrCreate(
            ['email' => env('ADMIN_EMAIL', 'admin@smartmirror.test')],
            [
                'tenant_id' => $tenant->id,
                'name' => env('ADMIN_NAME', 'Store Admin'),
                'password' => Hash::make(env('ADMIN_PASSWORD', 'ChangeMe123!')),
                'role' => UserRole::Owner,
                'status' => UserStatus::Active,
            ]
        );

        $tops = Category::query()->firstOrCreate(
            ['tenant_id' => $tenant->id, 'slug' => 'tops'],
            ['name' => 'T-Shirts & Tops', 'status' => CategoryStatus::Active]
        );

        $product = Product::query()->firstOrCreate(
            ['tenant_id' => $tenant->id, 'sku' => 'TSHIRT-001'],
            [
                'category_id' => $tops->id,
                'name' => 'Classic Smart Mirror T-Shirt',
                'description' => 'Demo garment for the smart mirror catalog.',
                'unit_price' => 799,
                'currency' => 'EGP',
                'status' => ProductStatus::Active,
            ]
        );

        if ($product->sizingCharts()->doesntExist()) {
            $product->sizingCharts()->createMany([
                ['size_label' => 'S', 'shoulder_width_cm' => 42, 'chest_width_cm' => 48, 'height_cm' => 66, 'sort_order' => 0],
                ['size_label' => 'M', 'shoulder_width_cm' => 44, 'chest_width_cm' => 51, 'height_cm' => 69, 'sort_order' => 1],
                ['size_label' => 'L', 'shoulder_width_cm' => 46, 'chest_width_cm' => 54, 'height_cm' => 72, 'sort_order' => 2],
            ]);
        }

        Mirror::query()->firstOrCreate(
            ['tenant_id' => $tenant->id, 'location_name' => 'Main Store Mirror'],
            ['public_id' => (string) Str::uuid(), 'pairing_code' => 'DEMO2026', 'status' => MirrorStatus::Pending]
        );
    }
}
