<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->boolean('is_demo_asset')->default(false)->after('texture_anchor')->index();
            $table->string('asset_source', 180)->nullable()->after('is_demo_asset');
            $table->string('asset_license', 180)->nullable()->after('asset_source');
            $table->json('image_qa')->nullable()->after('asset_license');
        });
    }

    public function down(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->dropColumn(['is_demo_asset', 'asset_source', 'asset_license', 'image_qa']);
        });
    }
};
