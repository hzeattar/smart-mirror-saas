<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\MirrorStatus;
use App\Enums\OrderStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Models\Order;
use App\Models\Product;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $tenantId = $request->user()->tenant_id;
        return response()->json(['stats' => [
            'products' => Product::query()->forTenant($tenantId)->count(),
            'orders_today' => Order::query()->forTenant($tenantId)->whereDate('created_at', today())->count(),
            'pending_orders' => Order::query()->forTenant($tenantId)->whereNotIn('status', [OrderStatus::Completed, OrderStatus::Cancelled])->count(),
            'online_mirrors' => Mirror::query()->forTenant($tenantId)->where('status', MirrorStatus::Online)->count(),
            'revenue_today' => (float) Order::query()->forTenant($tenantId)->whereDate('created_at', today())->where('status', '!=', OrderStatus::Cancelled)->sum('total'),
        ]]);
    }
}
