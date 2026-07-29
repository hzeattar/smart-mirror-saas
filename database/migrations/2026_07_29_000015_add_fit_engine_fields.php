<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->string('garment_type', 40)->default('top')->after('description')->index();
            $table->json('fit_profile')->nullable()->after('garment_type');
            $table->json('texture_anchor')->nullable()->after('fit_profile');
        });

        Schema::table('sizing_charts', function (Blueprint $table): void {
            $table->decimal('waist_width_cm', 6, 2)->nullable()->after('chest_width_cm');
            $table->decimal('hip_width_cm', 6, 2)->nullable()->after('waist_width_cm');
            $table->decimal('sleeve_length_cm', 6, 2)->nullable()->after('hip_width_cm');
            $table->decimal('fit_ease_cm', 6, 2)->default(4)->after('sleeve_length_cm');
        });
    }

    public function down(): void
    {
        Schema::table('sizing_charts', function (Blueprint $table): void {
            $table->dropColumn([
                'waist_width_cm',
                'hip_width_cm',
                'sleeve_length_cm',
                'fit_ease_cm',
            ]);
        });

        Schema::table('products', function (Blueprint $table): void {
            $table->dropColumn(['garment_type', 'fit_profile', 'texture_anchor']);
        });
    }
};
