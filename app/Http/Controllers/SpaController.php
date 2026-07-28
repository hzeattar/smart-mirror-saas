<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Response;

class SpaController extends Controller
{
    public function __invoke(): Response
    {
        return response()
            ->view('app')
            ->header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            ->header('Pragma', 'no-cache')
            ->header('Expires', '0');
    }

    public function status(): JsonResponse
    {
        $manifestPath = public_path('build/manifest.json');
        $manifest = is_file($manifestPath)
            ? json_decode((string) file_get_contents($manifestPath), true)
            : null;

        return response()->json([
            'status' => is_array($manifest) ? 'ready' : 'missing',
            'manifest_exists' => is_file($manifestPath),
            'javascript_entry' => $manifest['resources/js/app.js']['file'] ?? null,
            'stylesheet_entry' => $manifest['resources/css/app.css']['file'] ?? null,
            'javascript_css' => $manifest['resources/js/app.js']['css'] ?? [],
            'revision' => env('RAILWAY_GIT_COMMIT_SHA'),
        ])->header('Cache-Control', 'no-store');
    }
}
