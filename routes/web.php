<?php

use App\Http\Controllers\SpaController;
use App\Http\Controllers\TryOnResultController;
use Illuminate\Support\Facades\Route;

Route::get('/try-on-results/{job}', TryOnResultController::class);
Route::get('/frontend-status', [SpaController::class, 'status']);
Route::get('/{path?}', SpaController::class)->where('path', '^(?!api|up|storage|build|frontend-status).*$');
