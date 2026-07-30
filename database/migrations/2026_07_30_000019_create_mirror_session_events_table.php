<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('mirror_session_events', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->foreignId('mirror_id')->constrained()->cascadeOnDelete();
            $table->string('event', 80)->index();
            $table->decimal('fps', 6, 2)->nullable();
            $table->json('payload')->nullable();
            $table->timestamp('occurred_at')->index();
            $table->timestamps();

            $table->index(['tenant_id', 'occurred_at']);
            $table->index(['mirror_id', 'occurred_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('mirror_session_events');
    }
};
