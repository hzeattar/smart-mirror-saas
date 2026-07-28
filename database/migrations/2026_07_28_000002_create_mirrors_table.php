<?php

use App\Enums\MirrorStatus;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('mirrors', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('tenant_id')->constrained()->cascadeOnDelete();
            $table->string('pairing_code', 16)->unique();
            $table->string('location_name', 150);
            $table->string('status', 32)->default(MirrorStatus::Pending->value)->index();
            $table->timestamp('paired_at')->nullable();
            $table->timestamp('last_seen_at')->nullable()->index();
            $table->timestamps();
            $table->softDeletes();

            $table->index(['tenant_id', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('mirrors');
    }
};
