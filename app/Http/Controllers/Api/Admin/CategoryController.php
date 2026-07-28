<?php

namespace App\Http\Controllers\Api\Admin;

use App\Enums\CategoryStatus;
use App\Http\Controllers\Controller;
use App\Models\Category;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class CategoryController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        return response()->json(['categories' => Category::query()->forTenant($request->user()->tenant_id)->orderBy('sort_order')->get()]);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $request->validate(['name' => ['required','string','max:120'], 'status' => ['nullable', Rule::enum(CategoryStatus::class)]]);
        $category = Category::query()->create([
            ...$data,
            'tenant_id' => $request->user()->tenant_id,
            'slug' => Str::slug($data['name']).'-'.Str::lower(Str::random(4)),
        ]);
        return response()->json(['category' => $category], 201);
    }
}
