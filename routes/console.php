<?php

use Illuminate\Support\Facades\Artisan;

Artisan::command('smart-mirror:phase', function (): void {
    $this->info('Phases 1-4 complete: Laravel API, Vue dashboard, Python CV client, and Railway deployment.');
})->purpose('Show the currently implemented project phase');
