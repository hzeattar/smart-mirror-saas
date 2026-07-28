<?php

use App\Enums\BackgroundRemovalStatus;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->string('base_image_path')->nullable()->after('base_image_url');
            $table->string('texture_image_path')->nullable()->after('texture_image_url');
            $table->string('background_removal_status', 32)
                ->default(BackgroundRemovalStatus::NotRequested->value)
                ->index();
            $table->text('background_removal_error')->nullable();
            $table->timestamp('processed_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->dropColumn([
                'base_image_path',
                'texture_image_path',
                'background_removal_status',
                'background_removal_error',
                'processed_at',
            ]);
        });
    }
};
