<?php

namespace Tests\Feature;

use App\Enums\TenantStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Tenant;
use App\Models\User;
use App\Services\AiTryOn\AiProviderHealth;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class AiOperationsTest extends TestCase
{
    use RefreshDatabase;

    public function test_provider_health_command_publishes_nvidia_readiness(): void
    {
        config([
            'ai_tryon.provider' => 'nvidia',
            'ai_tryon.nvidia.api_key' => 'gateway-token',
            'ai_tryon.nvidia.endpoint' => 'https://gpu.example.test/v1/images/edits',
            'ai_tryon.nvidia.health_endpoint' => null,
        ]);
        Http::fake(['https://gpu.example.test/*' => Http::response(['status' => 'ready'])]);

        $this->artisan('ai:check-provider')->assertSuccessful();

        $health = app(AiProviderHealth::class)->snapshot();
        $this->assertTrue($health['available']);
        $this->assertSame('ready', $health['status']);
        Http::assertSent(fn ($request) => $request->url() === 'https://gpu.example.test/v1/health/ready'
            && $request->hasHeader('Authorization', 'Bearer gateway-token'));
    }

    public function test_runpod_reconciliation_starts_the_gpu_during_store_hours(): void
    {
        Carbon::setTestNow(Carbon::parse('2026-08-11 10:00:00', 'Africa/Cairo'));
        config([
            'runpod.enabled' => true,
            'runpod.api_base' => 'https://rest.runpod.test/v1',
            'runpod.api_key' => 'runpod-token',
            'runpod.pod_id' => 'pod-123',
            'runpod.timezone' => 'Africa/Cairo',
            'runpod.active_start' => '09:30',
            'runpod.active_end' => '22:15',
        ]);
        Http::fake([
            'https://rest.runpod.test/v1/pods/pod-123' => Http::response(['status' => 'STOPPED']),
            'https://rest.runpod.test/v1/pods/pod-123/start' => Http::response(['status' => 'STARTING']),
        ]);

        $this->artisan('runpod:reconcile')->assertSuccessful();

        Http::assertSent(fn ($request) => $request->method() === 'POST'
            && $request->url() === 'https://rest.runpod.test/v1/pods/pod-123/start');
        Carbon::setTestNow();
    }

    public function test_admin_dashboard_exposes_pilot_operational_metrics(): void
    {
        $tenant = Tenant::query()->create([
            'name' => 'Pilot Store',
            'domain' => 'pilot-operations.test',
            'status' => TenantStatus::Active,
        ]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Pilot Admin',
            'email' => 'pilot-operations@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        Sanctum::actingAs($user, ['admin']);

        $this->getJson('/api/admin/dashboard')
            ->assertOk()
            ->assertJsonStructure(['stats' => [
                'ai_average_processing_seconds',
                'ai_p95_processing_seconds',
                'ai_queue_backlog',
                'ai_failure_rate_today',
                'ai_provider_health' => ['available', 'status', 'checked_at'],
            ]]);
    }
}
