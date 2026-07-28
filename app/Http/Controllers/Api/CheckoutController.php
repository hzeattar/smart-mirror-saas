<?php

namespace App\Http\Controllers\Api;

use App\Enums\CheckoutStatus;
use App\Enums\OrderType;
use App\Http\Controllers\Controller;
use App\Http\Requests\CreateOrderRequest;
use App\Models\CheckoutSession;
use App\Models\Mirror;
use App\Models\Product;
use App\Services\OrderService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class CheckoutController extends Controller
{
    public function createSession(Request $request): JsonResponse
    {
        $data = $request->validate([
            'type' => ['required', Rule::enum(OrderType::class)],
            'items' => ['required', 'array', 'min:1', 'max:30'],
            'items.*.product_id' => ['required', 'integer'],
            'items.*.sizing_chart_id' => ['nullable', 'integer'],
            'items.*.quantity' => ['required', 'integer', 'min:1', 'max:20'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $productIds = collect($data['items'])->pluck('product_id')->unique();
        abort_unless(
            Product::query()->forTenant($mirror->tenant_id)->whereIn('id', $productIds)->count() === $productIds->count(),
            422,
            'Cart contains unavailable products.'
        );

        $plainToken = Str::random(48);
        $session = CheckoutSession::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'token_hash' => hash('sha256', $plainToken),
            'status' => CheckoutStatus::Open,
            'order_type' => $data['type'],
            'cart' => $data['items'],
            'expires_at' => now()->addMinutes((int) config('smart_mirror.checkout_ttl_minutes', 20)),
        ]);

        return response()->json([
            'session_id' => $session->public_id,
            'expires_at' => $session->expires_at->toIso8601String(),
            'checkout_url' => url('/checkout/'.$plainToken),
            'token' => $plainToken,
        ], 201);
    }

    public function show(string $token): JsonResponse
    {
        $session = $this->resolve($token)->load(['tenant', 'mirror']);
        $this->assertOpen($session);

        $products = Product::query()
            ->forTenant($session->tenant_id)
            ->with('sizingCharts')
            ->whereIn('id', collect($session->cart)->pluck('product_id'))
            ->get()->keyBy('id');

        $items = collect($session->cart)->map(function (array $item) use ($products): array {
            $product = $products->get($item['product_id']);
            $size = $product?->sizingCharts->firstWhere('id', $item['sizing_chart_id'] ?? null);
            return [
                ...$item,
                'name' => $product?->name,
                'image_url' => $product?->texture_image_url ?: $product?->base_image_url,
                'unit_price' => $product ? (float) $product->unit_price : 0,
                'currency' => $product?->currency,
                'size_label' => $size?->size_label,
            ];
        })->values();

        return response()->json([
            'session' => [
                'id' => $session->public_id,
                'type' => $session->order_type->value,
                'expires_at' => $session->expires_at->toIso8601String(),
                'tenant_name' => $session->tenant->name,
                'mirror_location' => $session->mirror->location_name,
                'items' => $items,
            ],
        ]);
    }

    public function createOrder(CreateOrderRequest $request, string $token, OrderService $orders): JsonResponse
    {
        $session = $this->resolve($token);
        $this->assertOpen($session);

        $payload = $request->validated();
        $payload['type'] = $session->order_type->value;
        $payload['items'] = $session->cart;

        $order = DB::transaction(function () use ($session, $payload, $orders) {
            $order = $orders->create($session->tenant_id, $session->mirror, $payload);
            $session->forceFill([
                'status' => CheckoutStatus::Completed,
                'completed_at' => now(),
                'order_id' => $order->id,
            ])->save();
            return $order;
        });

        return response()->json(['order' => $this->presentOrder($order)], 201);
    }

    public function directOrder(CreateOrderRequest $request, OrderService $orders): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $order = $orders->create($mirror->tenant_id, $mirror, $request->validated());
        return response()->json(['order' => $this->presentOrder($order)], 201);
    }

    private function resolve(string $token): CheckoutSession
    {
        return CheckoutSession::query()
            ->with('mirror')
            ->where('token_hash', hash('sha256', $token))
            ->firstOrFail();
    }

    private function assertOpen(CheckoutSession $session): void
    {
        if ($session->expires_at->isPast() && $session->status === CheckoutStatus::Open) {
            $session->update(['status' => CheckoutStatus::Expired]);
        }
        abort_unless($session->status === CheckoutStatus::Open, 410, 'Checkout session is no longer available.');
    }

    private function presentOrder($order): array
    {
        return [
            'id' => $order->public_id,
            'order_number' => $order->order_number,
            'status' => $order->status->value,
            'total' => (float) $order->total,
            'currency' => $order->currency,
            'items' => $order->items,
        ];
    }
}
