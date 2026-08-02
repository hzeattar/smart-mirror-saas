<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('mirror_session_events', function (Blueprint $table): void {
            $table->string('session_id', 80)->nullable()->after('mirror_id')->index();
            $table->unsignedInteger('sequence')->nullable()->after('session_id');
            $table->string('severity', 20)->default('info')->after('sequence')->index();
        });
    }

    public function down(): void
    {
        Schema::table('mirror_session_events', function (Blueprint $table): void {
            $table->dropColumn(['session_id', 'sequence', 'severity']);
        });
    }
};
