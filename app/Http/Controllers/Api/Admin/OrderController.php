<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\OrderStatus;
use App\Events\OrderStatusUpdated;
use App\Http\Controllers\Controller;
use App\Models\Order;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class OrderController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $query = Order::query()->forTenant($request->user()->tenant_id)->with(['items','mirror'])->latest();
        if ($request->filled('status')) $query->where('status', $request->string('status'));
        if ($request->filled('search')) {
            $term = '%'.$request->string('search').'%';
            $query->where(fn ($q) => $q->where('order_number','like',$term)->orWhere('customer_name','like',$term)->orWhere('customer_phone','like',$term));
        }
        return response()->json($query->paginate(30));
    }

    public function show(Request $request, Order $order): JsonResponse
    {
        $this->authorizeTenant($request, $order);
        return response()->json(['order' => $order->load(['items','mirror'])]);
    }

    public function updateStatus(Request $request, Order $order): JsonResponse
    {
        $this->authorizeTenant($request, $order);
        $data = $request->validate(['status' => ['required', Rule::enum(OrderStatus::class)]]);
        $order->update(['status' => $data['status']]);
        event(new OrderStatusUpdated($order));
        return response()->json(['order' => $order->fresh()->load(['items','mirror'])]);
    }

    private function authorizeTenant(Request $request, Order $order): void
    {
        abort_unless($order->tenant_id === $request->user()->tenant_id, 404);
    }
}
