<?php

namespace App\Events;

use App\Models\Order;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class OrderCreated implements ShouldBroadcastNow
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(public Order $order) {}

    public function broadcastOn(): array
    {
        return [new PrivateChannel('tenant.'.$this->order->tenant_id.'.orders')];
    }

    public function broadcastAs(): string
    {
        return 'order.created';
    }

    public function broadcastWith(): array
    {
        return [
            'order' => [
                'id' => $this->order->public_id,
                'order_number' => $this->order->order_number,
                'status' => $this->order->status->value,
                'type' => $this->order->type->value,
                'total' => (float) $this->order->total,
                'currency' => $this->order->currency,
                'customer_name' => $this->order->customer_name,
                'mirror_location' => $this->order->mirror?->location_name,
                'created_at' => $this->order->created_at->toIso8601String(),
            ],
        ];
    }
}
