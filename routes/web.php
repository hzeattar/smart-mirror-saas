<?php

use App\Http\Controllers\SpaController;
use Illuminate\Support\Facades\Route;

Route::get('/frontend-status', [SpaController::class, 'status']);
Route::get('/{path?}', SpaController::class)->where('path', '^(?!api|up|storage|build|frontend-status).*$');
