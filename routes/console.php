<?php

use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Schedule::command('tryon:purge-expired')->hourly()->withoutOverlapping();
Schedule::command('ai:check-provider')->everyMinute()->withoutOverlapping();
Schedule::command('runpod:reconcile')
    ->everyMinute()
    ->when(fn (): bool => (bool) config('runpod.enabled'))
    ->withoutOverlapping();

Artisan::command('smart-mirror:phase', function (): void {
    $this->info('Phases 1-4 complete: Laravel API, Vue dashboard, Python CV client, and Railway deployment.');
})->purpose('Show the currently implemented project phase');
