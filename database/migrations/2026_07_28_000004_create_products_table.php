<?php

use App\Enums\ProductStatus;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('products', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->foreignId('category_id')->nullable()->constrained()->nullOnDelete();
            $table->string('sku', 100)->nullable();
            $table->string('name', 180);
            $table->text('description')->nullable();
            $table->string('base_image_url', 2048)->nullable();
            $table->string('texture_image_url', 2048)->nullable();
            $table->decimal('unit_price', 12, 2)->default(0);
            $table->char('currency', 3)->default('EGP');
            $table->string('status', 32)->default(ProductStatus::Draft->value)->index();
            $table->timestamps();
            $table->softDeletes();

            $table->unique(['tenant_id', 'sku']);
            $table->index(['tenant_id', 'category_id', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
