<?php

namespace App\Http\Controllers\Api;

use App\Enums\ProductStatus;
use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Models\Product;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MirrorController extends Controller
{
    public function heartbeat(Request $request): JsonResponse
    {
        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        return response()->json(['ok' => true, 'server_time' => now()->toIso8601String(), 'mirror_id' => $mirror->id]);
    }

    public function catalog(Request $request, ?Mirror $mirror = null): JsonResponse
    {
        /** @var Mirror $authenticated */
        $authenticated = $request->attributes->get('mirror');
        abort_if($mirror && $mirror->id !== $authenticated->id, 403, 'Mirror cannot access another device catalog.');

        $products = Product::query()
            ->forTenant($authenticated->tenant_id)
            ->where('status', ProductStatus::Active)
            ->with(['category:id,name,slug', 'sizingCharts'])
            ->orderBy('name')
            ->get()
            ->map(fn (Product $product) => [
                'id' => $product->id,
                'sku' => $product->sku,
                'name' => $product->name,
                'description' => $product->description,
                'price' => (float) $product->unit_price,
                'currency' => $product->currency,
                'base_image_url' => $product->base_image_url,
                'texture_image_url' => $product->texture_image_url,
                'category' => $product->category,
                'sizes' => $product->sizingCharts->map(fn ($size) => [
                    'id' => $size->id,
                    'label' => $size->size_label,
                    'shoulder_width_cm' => (float) $size->shoulder_width_cm,
                    'chest_width_cm' => (float) $size->chest_width_cm,
                    'height_cm' => (float) $size->height_cm,
                ]),
            ]);

        return response()->json([
            'mirror' => ['id' => $authenticated->id, 'location_name' => $authenticated->location_name],
            'tenant' => ['id' => $authenticated->tenant->id, 'name' => $authenticated->tenant->name],
            'products' => $products,
            'generated_at' => now()->toIso8601String(),
        ]);
    }
}
