<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->unsignedSmallInteger('measurement_schema_version')->default(1)->after('garment_type');
            $table->string('measurement_basis', 40)->default('flat_garment')->after('measurement_schema_version');
            $table->string('asset_review_status', 24)->default('pending')->after('image_qa')->index();
            $table->text('asset_review_notes')->nullable()->after('asset_review_status');
            $table->timestamp('asset_reviewed_at')->nullable()->after('asset_review_notes');
        });

        Schema::table('sizing_charts', function (Blueprint $table): void {
            $table->decimal('shoulder_width_cm', 6, 2)->nullable()->change();
            $table->decimal('chest_width_cm', 6, 2)->nullable()->change();
            $table->decimal('inseam_length_cm', 6, 2)->nullable()->after('sleeve_length_cm');
        });
    }

    public function down(): void
    {
        Schema::table('sizing_charts', function (Blueprint $table): void {
            $table->dropColumn('inseam_length_cm');
            $table->decimal('shoulder_width_cm', 6, 2)->nullable(false)->change();
            $table->decimal('chest_width_cm', 6, 2)->nullable(false)->change();
        });
        Schema::table('products', fn (Blueprint $table) => $table->dropColumn([
            'measurement_schema_version',
            'measurement_basis',
            'asset_review_status',
            'asset_review_notes',
            'asset_reviewed_at',
        ]));
    }
};
