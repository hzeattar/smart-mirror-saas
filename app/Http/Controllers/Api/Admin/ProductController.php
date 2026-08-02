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
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;

class ProductController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $products = Product::query()
            ->forTenant($request->user()->tenant_id)
            ->with(['category', 'sizingCharts'])
            ->when(! $request->boolean('include_inactive'), fn ($query) => $query->where('status', ProductStatus::Active))
            ->latest()
            ->paginate(20);

        $products->getCollection()->transform(fn (Product $product) => [
            ...$product->toArray(),
            'readiness' => $this->readiness($product),
        ]);

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
                'base' => $this->imageQa($request->file('base_image'), 'base'),
                'texture' => $this->imageQa($request->file('texture_image'), 'texture'),
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
            'readiness' => $this->readiness($product),
        ], 201);
    }

    public function show(Request $request, Product $product): JsonResponse
    {
        $this->authorizeTenant($request, $product);

        return response()->json([
            'product' => $product->load(['category', 'sizingCharts']),
            'readiness' => $this->readiness($product),
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
                    'base' => $this->imageQa($request->file('base_image'), 'base'),
                ];
            }

            if ($request->hasFile('texture_image')) {
                $values['texture_image_path'] = $request->file('texture_image')->store('garments/textures', config('filesystems.default'));
                $values['texture_image_url'] = $disk->url($values['texture_image_path']);
                $values['background_removal_status'] = BackgroundRemovalStatus::Completed;
                $values['processed_at'] = now();
                $values['image_qa'] = [
                    ...($values['image_qa'] ?? ($product->image_qa ?? [])),
                    'texture' => $this->imageQa($request->file('texture_image'), 'texture'),
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
            'readiness' => $this->readiness($fresh),
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

    private function readiness(Product $product): array
    {
        $sizesReady = $product->relationLoaded('sizingCharts')
            ? $product->sizingCharts->count() >= 4
            : $product->sizingCharts()->count() >= 4;
        $hasImage = filled($product->base_image_url) || filled($product->base_image_path);
        $hasTexture = filled($product->texture_image_url) || filled($product->texture_image_path);
        $localGeneratedDemo = str_contains((string) $product->description, 'Local realistic demo garment texture')
            || str_starts_with((string) $product->sku, 'REAL-')
            || $product->is_demo_asset;
        $qa = $product->image_qa ?? [];
        $baseQaOk = in_array(($qa['base']['status'] ?? ($hasImage ? 'ok' : 'missing')), ['ok', 'warning', 'demo'], true);
        $textureQaOk = in_array(($qa['texture']['status'] ?? ($hasTexture ? 'ok' : 'missing')), ['ok', 'warning', 'demo'], true);
        $metadataReady = filled($product->asset_source) && filled($product->asset_license);
        $productionReady = $hasImage && $hasTexture && $sizesReady && $baseQaOk && $textureQaOk && $metadataReady && ! $localGeneratedDemo;
        $aiCandidate = $hasImage && $hasTexture && $sizesReady && $baseQaOk && $textureQaOk;
        $gate = match (true) {
            ! $hasImage => ['missing_photo', 'Missing Photo'],
            ! $hasTexture || ! $textureQaOk => ['needs_cutout', 'Needs Cutout'],
            ! $sizesReady => ['needs_sizes', 'Needs Sizes'],
            $productionReady => ['production_ready', 'Production Ready'],
            default => ['ai_candidate', 'AI Candidate'],
        };

        return [
            'image_ready' => $hasImage,
            'texture_ready' => $hasTexture,
            'sizes_ready' => $sizesReady,
            'qa_ready' => $baseQaOk && $textureQaOk,
            'metadata_ready' => $metadataReady,
            'ai_ready' => $aiCandidate,
            'production_asset_ready' => $productionReady,
            'status' => $gate[0],
            'label' => $gate[1],
            'issues' => [
                ...($qa['base']['issues'] ?? []),
                ...($qa['texture']['issues'] ?? []),
                ...($localGeneratedDemo ? ['demo_asset'] : []),
                ...(! $metadataReady ? ['missing_asset_metadata'] : []),
            ],
        ];
    }

    private function imageQa(?UploadedFile $file, string $kind): array
    {
        if (! $file) {
            return ['status' => 'missing', 'issues' => ['missing_file']];
        }

        $issues = [];
        $size = @getimagesize($file->getRealPath());
        $width = (int) ($size[0] ?? 0);
        $height = (int) ($size[1] ?? 0);
        $aspect = $height > 0 ? round($width / $height, 3) : 0.0;

        if ($width < 600 || $height < 600) {
            $issues[] = 'resolution_below_600px';
        }
        if ($aspect < 0.35 || $aspect > 2.2) {
            $issues[] = 'extreme_aspect_ratio';
        }

        $alphaCoverage = null;
        if ($kind === 'texture') {
            $alphaCoverage = $this->alphaCoverage($file);
            if ($alphaCoverage !== null && $alphaCoverage < 0.02) {
                $issues[] = 'no_transparent_cutout_detected';
            }
            if ($alphaCoverage !== null && $alphaCoverage > 0.85) {
                $issues[] = 'texture_mostly_transparent';
            }
        }

        $status = 'ok';
        if ($issues !== []) {
            $status = $kind === 'texture' && in_array('no_transparent_cutout_detected', $issues, true) ? 'failed' : 'warning';
        }

        return [
            'status' => $status,
            'width' => $width,
            'height' => $height,
            'aspect_ratio' => $aspect,
            'alpha_coverage' => $alphaCoverage,
            'issues' => $issues,
            'checked_at' => now()->toIso8601String(),
        ];
    }

    private function alphaCoverage(UploadedFile $file): ?float
    {
        if (! function_exists('imagecreatefromstring')) {
            return null;
        }

        $image = @imagecreatefromstring((string) file_get_contents($file->getRealPath()));
        if ($image === false) {
            return null;
        }

        $width = imagesx($image);
        $height = imagesy($image);
        $transparent = 0;
        $samples = 0;
        $stepX = max(1, (int) floor($width / 32));
        $stepY = max(1, (int) floor($height / 32));

        for ($y = 0; $y < $height; $y += $stepY) {
            for ($x = 0; $x < $width; $x += $stepX) {
                $rgba = imagecolorat($image, $x, $y);
                $alpha = ($rgba & 0x7F000000) >> 24;
                if ($alpha > 8) {
                    $transparent++;
                }
                $samples++;
            }
        }
        imagedestroy($image);

        return $samples > 0 ? round($transparent / $samples, 4) : null;
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
