<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('try_on_jobs', function (Blueprint $table): void {
            $table->foreignId('try_on_batch_id')
                ->nullable()
                ->after('id')
                ->constrained()
                ->nullOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('try_on_jobs', function (Blueprint $table): void {
            $table->dropConstrainedForeignId('try_on_batch_id');
        });
    }
};
