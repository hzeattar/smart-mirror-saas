<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Schema;
use Tests\TestCase;

class DatabaseSchemaTest extends TestCase
{
    use RefreshDatabase;

    public function test_phase_one_tables_exist(): void
    {
        foreach ([
            'tenants',
            'mirrors',
            'categories',
            'products',
            'sizing_charts',
            'orders',
            'order_items',
            'try_on_jobs',
        ] as $table) {
            $this->assertTrue(Schema::hasTable($table), "Missing table: {$table}");
        }
    }

    public function test_core_tenant_and_catalog_columns_exist(): void
    {
        $this->assertTrue(Schema::hasColumns('tenants', ['id', 'name', 'domain', 'status']));
        $this->assertTrue(Schema::hasColumns('mirrors', ['tenant_id', 'pairing_code', 'location_name', 'status']));
        $this->assertTrue(Schema::hasColumns('categories', ['tenant_id', 'name', 'slug']));
        $this->assertTrue(Schema::hasColumns('products', [
            'tenant_id',
            'category_id',
            'name',
            'base_image_url',
            'texture_image_url',
            'is_demo_asset',
            'asset_source',
            'asset_license',
            'image_qa',
        ]));
        $this->assertTrue(Schema::hasColumns('sizing_charts', [
            'product_id',
            'size_label',
            'shoulder_width_cm',
            'chest_width_cm',
            'height_cm',
        ]));
    }

    public function test_order_columns_exist(): void
    {
        $this->assertTrue(Schema::hasColumns('orders', [
            'tenant_id',
            'mirror_id',
            'type',
            'status',
            'subtotal',
            'total',
        ]));
        $this->assertTrue(Schema::hasColumns('order_items', [
            'order_id',
            'product_id',
            'sizing_chart_id',
            'product_name',
            'size_label',
            'quantity',
            'unit_price',
            'line_total',
        ]));
    }

    public function test_try_on_job_columns_exist(): void
    {
        $this->assertTrue(Schema::hasColumns('try_on_jobs', [
            'tenant_id',
            'mirror_id',
            'product_id',
            'status',
            'provider',
            'input_image_path',
            'result_image_path',
            'expires_at',
        ]));
    }
}
