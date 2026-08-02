<?php

namespace App\Services;

use App\Enums\ProductStatus;
use App\Models\Product;

class ProductReadinessService
{
    public function readiness(Product $product): array
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
            'mirror_catalog_ready' => $aiCandidate,
            'status' => $gate[0],
            'label' => $gate[1],
            'issues' => $this->issues($qa, $localGeneratedDemo, $metadataReady, $hasImage, $hasTexture, $sizesReady),
        ];
    }

    public function mirrorCatalogReady(Product $product): bool
    {
        return (bool) $this->readiness($product)['mirror_catalog_ready'];
    }

    public function availableForMirror(Product $product): bool
    {
        return $product->status === ProductStatus::Active && $this->mirrorCatalogReady($product);
    }

    private function issues(array $qa, bool $localGeneratedDemo, bool $metadataReady, bool $hasImage, bool $hasTexture, bool $sizesReady): array
    {
        return [
            ...(! $hasImage ? ['missing_photo'] : []),
            ...(! $hasTexture ? ['missing_cutout'] : []),
            ...(! $sizesReady ? ['needs_four_sizes'] : []),
            ...($qa['base']['issues'] ?? []),
            ...($qa['texture']['issues'] ?? []),
            ...($localGeneratedDemo ? ['demo_asset'] : []),
            ...(! $metadataReady ? ['missing_asset_metadata'] : []),
        ];
    }
}
