<?php

use App\Http\Controllers\Api\Admin\CategoryController;
use App\Http\Controllers\Api\Admin\DashboardController;
use App\Http\Controllers\Api\Admin\MirrorController as AdminMirrorController;
use App\Http\Controllers\Api\Admin\OrderController as AdminOrderController;
use App\Http\Controllers\Api\Admin\ProductController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\CheckoutController;
use App\Http\Controllers\Api\MirrorAuthController;
use App\Http\Controllers\Api\MirrorController;
use Illuminate\Support\Facades\Route;

Route::get('/health', fn () => ['ok' => true, 'time' => now()->toIso8601String()]);
Route::post('/auth/login', [AuthController::class, 'login'])->middleware('throttle:10,1');
Route::post('/mirrors/pair', [MirrorAuthController::class, 'pair'])->middleware('throttle:20,1');

Route::get('/checkout/{token}', [CheckoutController::class, 'show'])->middleware('throttle:60,1');
Route::post('/checkout/{token}/orders', [CheckoutController::class, 'createOrder'])->middleware('throttle:20,1');

Route::middleware(['mirror.auth', 'throttle:240,1'])->group(function (): void {
    Route::post('/mirror/heartbeat', [MirrorController::class, 'heartbeat']);
    Route::get('/mirror/catalog', [MirrorController::class, 'catalog']);
    Route::get('/mirrors/{mirror}/catalog', [MirrorController::class, 'catalog']);
    Route::post('/mirror/checkout-sessions', [CheckoutController::class, 'createSession']);
    Route::post('/mirror/orders', [CheckoutController::class, 'directOrder']);
});

Route::middleware(['auth:sanctum', 'user.active'])->group(function (): void {
    Route::get('/auth/me', [AuthController::class, 'me']);
    Route::post('/auth/logout', [AuthController::class, 'logout']);

    Route::prefix('admin')->group(function (): void {
        Route::get('/dashboard', DashboardController::class);
        Route::apiResource('products', ProductController::class);
        Route::post('/products/{product}/reprocess', [ProductController::class, 'reprocess']);
        Route::get('/orders', [AdminOrderController::class, 'index']);
        Route::get('/orders/{order}', [AdminOrderController::class, 'show']);
        Route::patch('/orders/{order}/status', [AdminOrderController::class, 'updateStatus']);
        Route::get('/categories', [CategoryController::class, 'index']);
        Route::post('/categories', [CategoryController::class, 'store']);
        Route::get('/mirrors', [AdminMirrorController::class, 'index']);
        Route::post('/mirrors', [AdminMirrorController::class, 'store']);
        Route::patch('/mirrors/{mirror}', [AdminMirrorController::class, 'update']);
        Route::post('/mirrors/{mirror}/rotate-code', [AdminMirrorController::class, 'rotatePairingCode']);
    });
});
