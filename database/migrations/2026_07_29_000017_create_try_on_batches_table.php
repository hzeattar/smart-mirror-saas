<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('try_on_batches', function (Blueprint $table): void {
            $table->id();
            $table->uuid('public_id')->unique();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->foreignId('mirror_id')->constrained()->cascadeOnDelete();
            $table->foreignId('sizing_chart_id')->nullable()->constrained()->nullOnDelete();
            $table->string('status', 30)->default('queued')->index();
            $table->string('provider', 60)->default('mock')->index();
            $table->string('input_image_path');
            $table->unsignedSmallInteger('outfit_count')->default(0);
            $table->unsignedSmallInteger('completed_count')->default(0);
            $table->unsignedSmallInteger('failed_count')->default(0);
            $table->text('error')->nullable();
            $table->timestamp('queued_at')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamp('failed_at')->nullable();
            $table->timestamp('expires_at')->nullable()->index();
            $table->timestamps();

            $table->index(['tenant_id', 'status', 'created_at']);
            $table->index(['mirror_id', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('try_on_batches');
    }
};
