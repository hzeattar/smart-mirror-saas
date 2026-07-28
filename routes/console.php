<?php

use Illuminate\Support\Facades\Artisan;

Artisan::command('smart-mirror:phase', function (): void {
    $this->info('Phase 1: Database architecture and Eloquent models.');
})->purpose('Show the currently implemented project phase');
