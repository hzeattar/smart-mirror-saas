<?php

namespace Tests\Feature;

use App\Models\Category;
use App\Models\Mirror;
use App\Models\Order;
use App\Models\OrderItem;
use App\Models\Product;
use App\Models\SizingChart;
use App\Models\Tenant;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Tests\TestCase;

class ModelRelationshipsTest extends TestCase
{
    public function test_expected_relationship_types_are_declared(): void
    {
        $tenant = new Tenant;
        $mirror = new Mirror;
        $category = new Category;
        $product = new Product;
        $size = new SizingChart;
        $order = new Order;
        $item = new OrderItem;

        $this->assertInstanceOf(HasMany::class, $tenant->mirrors());
        $this->assertInstanceOf(HasMany::class, $tenant->categories());
        $this->assertInstanceOf(HasMany::class, $tenant->products());
        $this->assertInstanceOf(HasMany::class, $tenant->orders());

        $this->assertInstanceOf(BelongsTo::class, $mirror->tenant());
        $this->assertInstanceOf(BelongsTo::class, $category->tenant());
        $this->assertInstanceOf(BelongsTo::class, $product->tenant());
        $this->assertInstanceOf(BelongsTo::class, $product->category());
        $this->assertInstanceOf(HasMany::class, $product->sizingCharts());
        $this->assertInstanceOf(BelongsTo::class, $size->product());
        $this->assertInstanceOf(BelongsTo::class, $order->tenant());
        $this->assertInstanceOf(BelongsTo::class, $order->mirror());
        $this->assertInstanceOf(HasMany::class, $order->items());
        $this->assertInstanceOf(BelongsTo::class, $item->order());
        $this->assertInstanceOf(BelongsTo::class, $item->product());
        $this->assertInstanceOf(BelongsTo::class, $item->sizingChart());
    }
}
