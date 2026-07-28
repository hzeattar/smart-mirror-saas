<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('mirrors', function (Blueprint $table): void {
            $table->uuid('public_id')->nullable()->unique()->after('id');
            $table->string('api_token_hash', 64)->nullable()->unique()->after('pairing_code');
            $table->string('device_name', 150)->nullable()->after('location_name');
            $table->string('app_version', 50)->nullable();
            $table->json('metadata')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('mirrors', function (Blueprint $table): void {
            $table->dropUnique(['public_id']);
            $table->dropUnique(['api_token_hash']);
            $table->dropColumn(['public_id', 'api_token_hash', 'device_name', 'app_version', 'metadata']);
        });
    }
};
