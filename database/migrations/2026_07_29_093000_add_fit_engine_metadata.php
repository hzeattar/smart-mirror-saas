<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            if (! Schema::hasColumn('products', 'garment_type')) {
                $table->string('garment_type', 32)->default('top')->after('description')->index();
            }
            if (! Schema::hasColumn('products', 'fit_profile')) {
                $table->string('fit_profile', 32)->default('regular')->after('garment_type');
            }
            if (! Schema::hasColumn('products', 'texture_anchor')) {
                $table->json('texture_anchor')->nullable()->after('fit_profile');
            }
        });

        Schema::table('sizing_charts', function (Blueprint $table): void {
            if (! Schema::hasColumn('sizing_charts', 'waist_width_cm')) {
                $table->decimal('waist_width_cm', 6, 2)->nullable()->after('chest_width_cm');
            }
            if (! Schema::hasColumn('sizing_charts', 'hip_width_cm')) {
                $table->decimal('hip_width_cm', 6, 2)->nullable()->after('waist_width_cm');
            }
            if (! Schema::hasColumn('sizing_charts', 'sleeve_length_cm')) {
                $table->decimal('sleeve_length_cm', 6, 2)->nullable()->after('hip_width_cm');
            }
            if (! Schema::hasColumn('sizing_charts', 'fit_ease_cm')) {
                $table->decimal('fit_ease_cm', 6, 2)->nullable()->after('sleeve_length_cm');
            }
        });
    }

    public function down(): void
    {
        Schema::table('sizing_charts', function (Blueprint $table): void {
            $columns = collect(['waist_width_cm', 'hip_width_cm', 'sleeve_length_cm', 'fit_ease_cm'])
                ->filter(fn (string $column): bool => Schema::hasColumn('sizing_charts', $column))
                ->all();
            if ($columns) {
                $table->dropColumn($columns);
            }
        });

        Schema::table('products', function (Blueprint $table): void {
            $columns = collect(['garment_type', 'fit_profile', 'texture_anchor'])
                ->filter(fn (string $column): bool => Schema::hasColumn('products', $column))
                ->all();
            if ($columns) {
                $table->dropColumn($columns);
            }
        });
    }
};
