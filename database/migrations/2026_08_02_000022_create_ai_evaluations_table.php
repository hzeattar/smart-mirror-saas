<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('ai_evaluations', function (Blueprint $table): void {
            $table->id();
            $table->uuid('public_id')->unique();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->foreignId('mirror_id')->nullable()->constrained()->nullOnDelete();
            $table->string('provider', 60)->default('mock')->index();
            $table->string('status', 30)->default('queued')->index();
            $table->unsignedSmallInteger('sample_count')->default(0);
            $table->unsignedSmallInteger('product_count')->default(0);
            $table->unsignedSmallInteger('item_count')->default(0);
            $table->unsignedSmallInteger('completed_count')->default(0);
            $table->unsignedSmallInteger('failed_count')->default(0);
            $table->unsignedSmallInteger('good_count')->default(0);
            $table->unsignedSmallInteger('usable_count')->default(0);
            $table->unsignedSmallInteger('bad_count')->default(0);
            $table->text('error')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamp('failed_at')->nullable();
            $table->timestamps();

            $table->index(['tenant_id', 'status', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ai_evaluations');
    }
};
