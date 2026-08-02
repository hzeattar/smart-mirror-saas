<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\BackgroundRemovalStatus;
use App\Enums\ProductStatus;
use App\Http\Controllers\Controller;
use App\Jobs\ProcessGarmentImage;
use App\Models\Category;
use App\Models\Product;
use App\Services\ImageQaService;
use App\Services\ProductReadinessService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;

class ProductController extends Controller
{
    public function __construct(
        private readonly ProductReadinessService $readiness,
        private readonly ImageQaService $imageQa,
    ) {}

    public function index(Request $request): JsonResponse
    {
        $query = Product::query()
            ->forTenant($request->user()->tenant_id)
            ->with(['category', 'sizingCharts'])
            ->when(! $request->boolean('include_inactive'), fn ($query) => $query->where('status', ProductStatus::Active))
            ->latest();

        $readiness = $request->string('readiness')->toString();
        if ($readiness !== '' && $readiness !== 'all') {
            $page = max(1, (int) $request->integer('page', 1));
            $perPage = 20;
            $filtered = $query->get()
                ->filter(fn (Product $product) => $this->matchesReadinessFilter($product, $readiness))
                ->values()
                ->map(fn (Product $product) => $this->present($product));

            return response()->json(new LengthAwarePaginator(
                $filtered->forPage($page, $perPage)->values(),
                $filtered->count(),
                $perPage,
                $page,
                ['path' => $request->url(), 'query' => $request->query()],
            ));
        }

        $products = $query->paginate(20);

        $products->getCollection()->transform(fn (Product $product) => $this->present($product));

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
            $imageQa = [
                'base' => $this->imageQa->fromUpload($request->file('base_image'), 'base'),
                'texture' => $this->imageQa->fromUpload($request->file('texture_image'), 'texture'),
            ];

            $product = Product::query()->create([
                'tenant_id' => $tenantId,
                'category_id' => $data['category_id'] ?? null,
                'sku' => $data['sku'] ?? null,
                'name' => $data['name'],
                'description' => $data['description'] ?? null,
                'garment_type' => $data['garment_type'] ?? 'top',
                'fit_profile' => $data['fit_profile'] ?? $this->defaultFitProfile(),
                'texture_anchor' => $data['texture_anchor'] ?? $this->defaultTextureAnchor(),
                'is_demo_asset' => $request->boolean('is_demo_asset'),
                'asset_source' => $data['asset_source'] ?? null,
                'asset_license' => $data['asset_license'] ?? null,
                'image_qa' => $imageQa,
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

        return response()->json([
            'product' => $product->load(['category', 'sizingCharts']),
            'readiness' => $this->readiness->readiness($product),
        ], 201);
    }

    public function show(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);

        return response()->json([
            'product' => $product->load(['category', 'sizingCharts']),
            'readiness' => $this->readiness->readiness($product),
        ]);
    }

    public function update(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);
        $data = $this->validateProduct($request, true);
        $this->assertCategory($product->tenant_id, $data['category_id'] ?? null);

        DB::transaction(function () use ($request, $product, $data): void {
            $disk = Storage::disk(config('filesystems.default'));
            $values = collect($data)
                ->except(['sizes', 'base_image', 'texture_image'])
                ->all();
            if (array_key_exists('is_demo_asset', $data)) {
                $values['is_demo_asset'] = $request->boolean('is_demo_asset');
            }

            if ($request->hasFile('base_image')) {
                $values['base_image_path'] = $request->file('base_image')->store('garments/originals', config('filesystems.default'));
                $values['base_image_url'] = $disk->url($values['base_image_path']);
                $values['background_removal_status'] = BackgroundRemovalStatus::Pending;
                $values['image_qa'] = [
                    ...($product->image_qa ?? []),
                    'base' => $this->imageQa->fromUpload($request->file('base_image'), 'base'),
                ];
            }

            if ($request->hasFile('texture_image')) {
                $values['texture_image_path'] = $request->file('texture_image')->store('garments/textures', config('filesystems.default'));
                $values['texture_image_url'] = $disk->url($values['texture_image_path']);
                $values['background_removal_status'] = BackgroundRemovalStatus::Completed;
                $values['processed_at'] = now();
                $values['image_qa'] = [
                    ...($values['image_qa'] ?? ($product->image_qa ?? [])),
                    'texture' => $this->imageQa->fromUpload($request->file('texture_image'), 'texture'),
                ];
            }

            $product->update($values);
            if (array_key_exists('sizes', $data)) {
                $this->syncSizes($product, $data['sizes']);
            }
        });

        if ($product->background_removal_status === BackgroundRemovalStatus::Pending) {
            ProcessGarmentImage::dispatch($product->id);
        }

        $fresh = $product->fresh()->load(['category', 'sizingCharts']);

        return response()->json([
            'product' => $fresh,
            'readiness' => $this->readiness->readiness($fresh),
        ]);
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
        $product->update([
            'background_removal_status' => BackgroundRemovalStatus::Pending,
            'background_removal_error' => null,
        ]);
        ProcessGarmentImage::dispatch($product->id);

        return response()->json(['message' => 'Image processing queued.']);
    }

    private function validateProduct(Request $request, bool $partial = false): array
    {
        $prefix = $partial ? 'sometimes' : 'required';

        return $request->validate([
            'name' => [$prefix, 'string', 'max:180'],
            'sku' => ['nullable', 'string', 'max:100'],
            'category_id' => ['nullable', 'integer'],
            'description' => ['nullable', 'string', 'max:3000'],
            'garment_type' => [$partial ? 'sometimes' : 'required', Rule::in(['top', 'shirt', 'tshirt', 'polo', 'hoodie', 'jacket', 'dress', 'trousers', 'pants', 'jeans', 'suit'])],
            'unit_price' => [$prefix, 'numeric', 'min:0', 'max:9999999999'],
            'currency' => ['nullable', 'string', 'size:3'],
            'status' => ['nullable', Rule::enum(ProductStatus::class)],
            'is_demo_asset' => ['nullable', 'boolean'],
            'asset_source' => ['nullable', 'string', 'max:180'],
            'asset_license' => ['nullable', 'string', 'max:180'],
            'base_image' => ['nullable', 'image', 'max:12288'],
            'texture_image' => ['nullable', 'image', 'mimes:png,webp', 'max:12288'],

            'fit_profile' => ['nullable', 'array'],
            'fit_profile.shoulder_expand' => ['nullable', 'numeric', 'min:0', 'max:0.5'],
            'fit_profile.top_offset_ratio' => ['nullable', 'numeric', 'min:-0.2', 'max:0.4'],
            'fit_profile.height_ratio' => ['nullable', 'numeric', 'min:0.8', 'max:2'],
            'fit_profile.forearm_occlusion' => ['nullable', 'boolean'],

            'texture_anchor' => ['nullable', 'array'],
            'texture_anchor.left' => ['nullable', 'numeric', 'min:0', 'max:0.45'],
            'texture_anchor.right' => ['nullable', 'numeric', 'min:0', 'max:0.45'],
            'texture_anchor.top' => ['nullable', 'numeric', 'min:0', 'max:0.45'],
            'texture_anchor.bottom' => ['nullable', 'numeric', 'min:0', 'max:0.45'],

            'sizes' => [$partial ? 'sometimes' : 'required', 'array', 'min:1', 'max:30'],
            'sizes.*.size_label' => ['required', 'string', 'max:32'],
            'sizes.*.shoulder_width_cm' => ['required', 'numeric', 'min:1', 'max:300'],
            'sizes.*.chest_width_cm' => ['required', 'numeric', 'min:1', 'max:300'],
            'sizes.*.waist_width_cm' => ['nullable', 'numeric', 'min:1', 'max:300'],
            'sizes.*.hip_width_cm' => ['nullable', 'numeric', 'min:1', 'max:300'],
            'sizes.*.sleeve_length_cm' => ['nullable', 'numeric', 'min:0', 'max:300'],
            'sizes.*.fit_ease_cm' => ['nullable', 'numeric', 'min:0', 'max:50'],
            'sizes.*.height_cm' => ['required', 'numeric', 'min:1', 'max:300'],
        ]);
    }

    private function syncSizes(Product $product, array $sizes): void
    {
        $product->sizingCharts()->delete();
        $product->sizingCharts()->createMany(
            collect($sizes)
                ->values()
                ->map(fn (array $size, int $index) => [
                    ...$size,
                    'fit_ease_cm' => $size['fit_ease_cm'] ?? 4,
                    'sort_order' => $index,
                ])
                ->all()
        );
    }

    private function defaultFitProfile(): array
    {
        return [
            'shoulder_expand' => 0.10,
            'top_offset_ratio' => 0.07,
            'height_ratio' => 1.28,
            'forearm_occlusion' => true,
        ];
    }

    private function defaultTextureAnchor(): array
    {
        return ['left' => 0, 'right' => 0, 'top' => 0, 'bottom' => 0];
    }

    private function present(Product $product): array
    {
        return [
            ...$product->toArray(),
            'readiness' => $this->readiness->readiness($product),
        ];
    }

    private function matchesReadinessFilter(Product $product, string $filter): bool
    {
        $readiness = $this->readiness->readiness($product);

        return match ($filter) {
            'production_ready' => (bool) $readiness['production_asset_ready'],
            'ai_candidate' => (bool) $readiness['ai_ready'],
            'needs_work' => ! (bool) $readiness['ai_ready'],
            default => true,
        };
    }

    private function assertCategory(int $tenantId, ?int $categoryId): void
    {
        if ($categoryId) {
            abort_unless(
                Category::query()->forTenant($tenantId)->whereKey($categoryId)->exists(),
                422,
                'Category does not belong to this tenant.'
            );
        }
    }

    private function authorizeTenant(Request $request, Product $product): void
    {
        abort_unless($product->tenant_id === $request->user()->tenant_id, 404);
    }
}
