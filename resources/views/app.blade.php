@php
    $manifestPath = public_path('build/manifest.json');
    $manifest = is_file($manifestPath)
        ? json_decode((string) file_get_contents($manifestPath), true)
        : null;

    $jsEntry = is_array($manifest) ? ($manifest['resources/js/app.js'] ?? null) : null;
    $cssFiles = [];

    if (is_array($manifest)) {
        $standaloneCss = $manifest['resources/css/app.css']['file'] ?? null;
        if ($standaloneCss) {
            $cssFiles[] = $standaloneCss;
        }

        foreach (($jsEntry['css'] ?? []) as $cssFile) {
            $cssFiles[] = $cssFile;
        }

        $cssFiles = array_values(array_unique($cssFiles));
    }
@endphp
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#07111f">
    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">
    <title>{{ config('app.name', 'Smart Mirror') }}</title>

    @foreach ($cssFiles as $cssFile)
        <link rel="stylesheet" href="/build/{{ ltrim($cssFile, '/') }}?v={{ substr((string) env('RAILWAY_GIT_COMMIT_SHA', 'local'), 0, 12) }}">
    @endforeach

    <style>
        html, body { margin: 0; min-height: 100%; background: #07111f; }
        .boot-screen { min-height: 100vh; display: grid; place-items: center; padding: 24px; color: #e5eefb; font-family: Inter, Arial, sans-serif; background: radial-gradient(circle at 75% 0%, #123a56 0, transparent 38%), #07111f; }
        .boot-card { width: min(560px, 92vw); padding: 32px; border: 1px solid #26364c; border-radius: 20px; background: #0c1726; box-shadow: 0 24px 80px rgba(0,0,0,.35); }
        .boot-card strong { display: block; margin-bottom: 10px; font-size: 24px; }
        .boot-card p { margin: 0; color: #9db0c5; line-height: 1.65; }
        .boot-card code { color: #7dd3fc; }
    </style>
</head>
<body>
    <div id="app">
        <main class="boot-screen">
            <section class="boot-card">
                <strong>Loading Smart Mirror…</strong>
                <p>The Laravel application is online and the Vue dashboard is starting.</p>
            </section>
        </main>
    </div>

    @if (is_array($jsEntry) && ! empty($jsEntry['file']))
        <script type="module" src="/build/{{ ltrim($jsEntry['file'], '/') }}?v={{ substr((string) env('RAILWAY_GIT_COMMIT_SHA', 'local'), 0, 12) }}"></script>
    @else
        <script>
            document.querySelector('.boot-card').innerHTML = `
                <strong>Frontend bundle is missing</strong>
                <p>Laravel is running, but <code>public/build/manifest.json</code> does not contain the Vue entry. Open <code>/frontend-status</code> for the deployment status.</p>
            `;
        </script>
    @endif

    <script>
        window.setTimeout(() => {
            const loadingCard = document.querySelector('.boot-card');
            if (loadingCard) {
                loadingCard.innerHTML = `
                    <strong>Vue did not start</strong>
                    <p>The frontend file was referenced but did not mount. Check the browser console and <code>/frontend-status</code>.</p>
                `;
            }
        }, 8000);
    </script>
</body>
</html>
