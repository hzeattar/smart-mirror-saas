<?php

namespace App\Services;

use App\Models\Product;

class ProductMeasurementService
{
    public const SCHEMA_VERSION = 1;

    public const BASIS = 'flat_garment';

    public function requiredFields(string $garmentType): array
    {
        return match ($garmentType) {
            'trousers', 'pants', 'jeans' => ['waist_width_cm', 'hip_width_cm', 'height_cm', 'inseam_length_cm'],
            'dress' => ['shoulder_width_cm', 'chest_width_cm', 'waist_width_cm', 'hip_width_cm', 'height_cm'],
            'shirt', 'tshirt', 'polo', 'hoodie', 'jacket', 'suit' => ['shoulder_width_cm', 'chest_width_cm', 'height_cm'],
            default => ['shoulder_width_cm', 'chest_width_cm', 'height_cm'],
        };
    }

    public function reasons(Product $product): array
    {
        $charts = $product->relationLoaded('sizingCharts')
            ? $product->sizingCharts
            : $product->sizingCharts()->get();
        $reasons = [];

        if ((int) $product->measurement_schema_version !== self::SCHEMA_VERSION) {
            $reasons[] = 'unsupported_measurement_schema';
        }
        if ($product->measurement_basis !== self::BASIS) {
            $reasons[] = 'measurement_basis_must_be_flat_garment';
        }
        if ($charts->isEmpty()) {
            $reasons[] = 'missing_sizes';
        }

        $required = $this->requiredFields((string) $product->garment_type);
        foreach ($charts as $chart) {
            foreach ($required as $field) {
                if (! is_numeric($chart->{$field}) || (float) $chart->{$field} <= 0) {
                    $reasons[] = 'size_'.strtolower((string) $chart->size_label).'_missing_'.$field;
                }
            }
        }

        return array_values(array_unique($reasons));
    }

    public function ready(Product $product): bool
    {
        return $this->reasons($product) === [];
    }
}
