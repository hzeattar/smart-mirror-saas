<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\BackgroundRemovalStatus;
use App\Enums\ProductStatus;
use App\Http\Controllers\Controller;
use App\Jobs\ProcessGarmentImage;
use App\Models\Category;
use App\Models\Product;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;

class ProductController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $products = Product::query()->forTenant($request->user()->tenant_id)
            ->with(['category', 'sizingCharts'])->latest()->paginate(20);
        return response()->json($products);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->validateProduct($request);
        $tenantId = $request->user()->tenant_id;
        $this->assertCategory($tenantId, $data['category_id'] ?? null);

        $product = DB::transaction(function () use ($request, $data, $tenantId): Product {
            $basePath = $request->file('base_image')?->store('garments/originals', config('filesystems.default'));
            $texturePath = $request->file('texture_image')?->store('garments/textures', config('filesystems.default'));
            $disk = Storage::disk(config('filesystems.default'));

            $product = Product::query()->create([
                'tenant_id' => $tenantId,
                'category_id' => $data['category_id'] ?? null,
                'sku' => $data['sku'] ?? null,
                'name' => $data['name'],
                'description' => $data['description'] ?? null,
                'unit_price' => $data['unit_price'],
                'currency' => strtoupper($data['currency'] ?? 'EGP'),
                'status' => $data['status'] ?? ProductStatus::Draft,
                'base_image_path' => $basePath,
                'base_image_url' => $basePath ? $disk->url($basePath) : null,
                'texture_image_path' => $texturePath,
                'texture_image_url' => $texturePath ? $disk->url($texturePath) : null,
                'background_removal_status' => $texturePath
                    ? BackgroundRemovalStatus::Completed
                    : ($basePath ? BackgroundRemovalStatus::Pending : BackgroundRemovalStatus::NotRequested),
            ]);
            $this->syncSizes($product, $data['sizes']);
            return $product;
        });

        if ($product->base_image_path && ! $product->texture_image_path) {
            ProcessGarmentImage::dispatch($product->id);
        }

        return response()->json(['product' => $product->load(['category','sizingCharts'])], 201);
    }

    public function show(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);
        return response()->json(['product' => $product->load(['category','sizingCharts'])]);
    }

    public function update(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);
        $data = $this->validateProduct($request, true);
        $this->assertCategory($product->tenant_id, $data['category_id'] ?? null);

        DB::transaction(function () use ($request, $product, $data): void {
            $disk = Storage::disk(config('filesystems.default'));
            $values = collect($data)->except(['sizes','base_image','texture_image'])->all();

            if ($request->hasFile('base_image')) {
                $values['base_image_path'] = $request->file('base_image')->store('garments/originals', config('filesystems.default'));
                $values['base_image_url'] = $disk->url($values['base_image_path']);
                $values['background_removal_status'] = BackgroundRemovalStatus::Pending;
            }
            if ($request->hasFile('texture_image')) {
                $values['texture_image_path'] = $request->file('texture_image')->store('garments/textures', config('filesystems.default'));
                $values['texture_image_url'] = $disk->url($values['texture_image_path']);
                $values['background_removal_status'] = BackgroundRemovalStatus::Completed;
                $values['processed_at'] = now();
            }

            $product->update($values);
            if (array_key_exists('sizes', $data)) {
                $this->syncSizes($product, $data['sizes']);
            }
        });

        if ($product->background_removal_status === BackgroundRemovalStatus::Pending) {
            ProcessGarmentImage::dispatch($product->id);
        }

        return response()->json(['product' => $product->fresh()->load(['category','sizingCharts'])]);
    }

    public function destroy(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);
        $product->delete();
        return response()->json(status: 204);
    }

    public function reprocess(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);
        abort_unless($product->base_image_path, 422, 'Upload a base image first.');
        $product->update(['background_removal_status' => BackgroundRemovalStatus::Pending, 'background_removal_error' => null]);
        ProcessGarmentImage::dispatch($product->id);
        return response()->json(['message' => 'Image processing queued.']);
    }

    private function validateProduct(Request $request, bool $partial = false): array
    {
        $prefix = $partial ? 'sometimes' : 'required';
        return $request->validate([
            'name' => [$prefix, 'string', 'max:180'],
            'sku' => ['nullable','string','max:100'],
            'category_id' => ['nullable','integer'],
            'description' => ['nullable','string','max:3000'],
            'unit_price' => [$prefix,'numeric','min:0','max:9999999999'],
            'currency' => ['nullable','string','size:3'],
            'status' => ['nullable', Rule::enum(ProductStatus::class)],
            'base_image' => ['nullable','image','max:12288'],
            'texture_image' => ['nullable','image','mimes:png,webp','max:12288'],
            'sizes' => [$partial ? 'sometimes' : 'required','array','min:1','max:30'],
            'sizes.*.size_label' => ['required','string','max:32'],
            'sizes.*.shoulder_width_cm' => ['required','numeric','min:1','max:300'],
            'sizes.*.chest_width_cm' => ['required','numeric','min:1','max:300'],
            'sizes.*.height_cm' => ['required','numeric','min:1','max:300'],
        ]);
    }

    private function syncSizes(Product $product, array $sizes): void
    {
        $product->sizingCharts()->delete();
        $product->sizingCharts()->createMany(collect($sizes)->values()->map(fn ($size, $index) => [...$size, 'sort_order' => $index])->all());
    }

    private function assertCategory(int $tenantId, ?int $categoryId): void
    {
        if ($categoryId) {
            abort_unless(Category::query()->forTenant($tenantId)->whereKey($categoryId)->exists(), 422, 'Category does not belong to this tenant.');
        }
    }

    private function authorizeTenant(Request $request, Product $product): void
    {
        abort_unless($product->tenant_id === $request->user()->tenant_id, 404);
    }
}
