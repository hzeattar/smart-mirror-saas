<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('ai_evaluation_items', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('ai_evaluation_id')->constrained()->cascadeOnDelete();
            $table->foreignId('try_on_job_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('product_id')->constrained()->cascadeOnDelete();
            $table->string('sample_image_path');
            $table->string('rating', 20)->nullable()->index();
            $table->text('notes')->nullable();
            $table->unsignedSmallInteger('sort_order')->default(0);
            $table->timestamps();

            $table->index(['ai_evaluation_id', 'sort_order']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ai_evaluation_items');
    }
};
