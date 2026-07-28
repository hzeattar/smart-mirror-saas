<?php

namespace App\Services;

use App\Enums\OrderStatus;
use App\Events\OrderCreated;
use App\Models\Mirror;
use App\Models\Order;
use App\Models\Product;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class OrderService
{
    public function create(int $tenantId, ?Mirror $mirror, array $payload): Order
    {
        return DB::transaction(function () use ($tenantId, $mirror, $payload): Order {
            $productIds = collect($payload['items'])->pluck('product_id')->unique()->values();
            $products = Product::query()
                ->forTenant($tenantId)
                ->with('sizingCharts')
                ->whereIn('id', $productIds)
                ->get()
                ->keyBy('id');

            if ($products->count() !== $productIds->count()) {
                throw ValidationException::withMessages(['items' => ['One or more products are unavailable.']]);
            }

            $normalized = [];
            $subtotal = 0.0;
            $currency = null;

            foreach ($payload['items'] as $item) {
                $product = $products->get($item['product_id']);
                $size = isset($item['sizing_chart_id'])
                    ? $product->sizingCharts->firstWhere('id', $item['sizing_chart_id'])
                    : null;
                if (isset($item['sizing_chart_id']) && ! $size) {
                    throw ValidationException::withMessages(['items' => ['Selected size does not belong to its product.']]);
                }

                $quantity = max(1, (int) $item['quantity']);
                $unitPrice = (float) $product->unit_price;
                $lineTotal = round($unitPrice * $quantity, 2);
                $subtotal += $lineTotal;
                $currency ??= $product->currency;
                if ($currency !== $product->currency) {
                    throw ValidationException::withMessages(['items' => ['All items must use the same currency.']]);
                }

                $normalized[] = [
                    'product_id' => $product->id,
                    'sizing_chart_id' => $size?->id,
                    'product_name' => $product->name,
                    'sku' => $product->sku,
                    'size_label' => $size?->size_label,
                    'quantity' => $quantity,
                    'unit_price' => $unitPrice,
                    'line_total' => $lineTotal,
                ];
            }

            $order = Order::query()->create([
                'public_id' => (string) Str::uuid(),
                'order_number' => 'SM-'.now()->format('ymd').'-'.strtoupper(Str::random(6)),
                'tenant_id' => $tenantId,
                'mirror_id' => $mirror?->id,
                'type' => $payload['type'],
                'status' => OrderStatus::Pending,
                'customer_name' => $payload['customer_name'] ?? null,
                'customer_phone' => $payload['customer_phone'] ?? null,
                'customer_email' => $payload['customer_email'] ?? null,
                'delivery_address' => $payload['delivery_address'] ?? null,
                'subtotal' => $subtotal,
                'total' => $subtotal,
                'currency' => $currency ?: 'EGP',
                'notes' => $payload['notes'] ?? null,
            ]);

            $order->items()->createMany($normalized);
            $order->load(['items', 'mirror']);
            DB::afterCommit(fn () => event(new OrderCreated($order)));

            return $order;
        });
    }
}
