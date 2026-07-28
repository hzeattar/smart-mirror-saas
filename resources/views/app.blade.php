<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#07111f">
    <title>{{ config('app.name', 'Smart Mirror') }}</title>
    @if (is_file(public_path('build/manifest.json')))
        @vite(['resources/css/app.css', 'resources/js/app.js'])
    @else
        <style>
            body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #07111f; color: #e5eefb; font-family: Arial, sans-serif; }
            .build-error { max-width: 680px; padding: 32px; border: 1px solid #26364c; border-radius: 18px; background: #0c1726; box-shadow: 0 24px 80px rgba(0,0,0,.35); }
            .build-error h1 { margin-top: 0; }
            .build-error code { color: #7dd3fc; }
        </style>
    @endif
</head>
<body>
@if (is_file(public_path('build/manifest.json')))
    <div id="app"></div>
@else
    <main class="build-error">
        <h1>Smart Mirror frontend is not built</h1>
        <p>The Laravel service is running, but the Vue production bundle is missing.</p>
        <p>Railway must complete <code>npm install</code> and <code>npm run build</code> during the build phase.</p>
    </main>
@endif
</body>
</html>
