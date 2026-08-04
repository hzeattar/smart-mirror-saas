<?php

use App\Enums\LiveRestyleStatus;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('live_restyle_sessions', function (Blueprint $table): void {
            $table->id();
            $table->uuid('public_id')->unique();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->foreignId('mirror_id')->constrained()->cascadeOnDelete();
            $table->string('provider', 40)->default('fal')->index();
            $table->string('model', 150)->default('decart/lucy2-vton/realtime');
            $table->string('status', 32)->default(LiveRestyleStatus::Active->value)->index();
            $table->unsignedSmallInteger('max_seconds')->default(20);
            $table->unsignedInteger('daily_seconds_limit')->nullable();
            $table->unsignedInteger('duration_seconds')->nullable();
            $table->decimal('estimated_cost_usd', 10, 4)->default(0);
            $table->text('error')->nullable();
            $table->json('metadata')->nullable();
            $table->timestamp('started_at')->nullable()->index();
            $table->timestamp('ended_at')->nullable();
            $table->timestamp('expires_at')->nullable()->index();
            $table->timestamps();

            $table->index(['tenant_id', 'mirror_id', 'created_at']);
            $table->index(['provider', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('live_restyle_sessions');
    }
};
