<?php

namespace App\Providers;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Broadcast;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        Model::shouldBeStrict(! app()->isProduction());
        Model::unguard(false);

        Broadcast::routes([
            'prefix' => 'api',
            'middleware' => ['api', 'auth:sanctum', 'user.active'],
        ]);

        require base_path('routes/channels.php');
    }
}
