<?php

namespace Tests\Feature;

use App\Enums\MirrorStatus;
use App\Enums\ProductStatus;
use App\Enums\TenantStatus;
use App\Enums\TryOnJobStatus;
use App\Enums\UserRole;
use App\Enums\UserStatus;
use App\Models\Mirror;
use App\Models\Product;
use App\Models\Tenant;
use App\Models\TryOnBatch;
use App\Models\TryOnJob;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class TryOnJobTest extends TestCase
{
    use RefreshDatabase;

    public function test_mirror_creates_and_reads_mock_try_on_job(): void
    {
        Storage::fake('local');
        config(['filesystems.default' => 'local', 'ai_tryon.provider' => 'mock']);

        [$tenant, $mirror, $token, $product, $size] = $this->mirrorFixture();

        $response = $this->withToken($token)->post('/api/mirror/try-on-jobs', [
            'product_id' => $product->id,
            'sizing_chart_id' => $size->id,
            'snapshot' => UploadedFile::fake()->image('snapshot.jpg', 640, 480),
        ])->assertCreated();

        $jobId = $response->json('job.id');
        $this->assertDatabaseHas('try_on_jobs', [
            'public_id' => $jobId,
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'product_id' => $product->id,
            'status' => TryOnJobStatus::Completed->value,
        ]);

        $resultPath = TryOnJob::query()->where('public_id', $jobId)->value('result_image_path');
        Storage::disk('local')->assertExists($resultPath);

        $this->withToken($token)->getJson('/api/mirror/try-on-jobs/'.$jobId)
            ->assertOk()
            ->assertJsonPath('job.status', 'completed')
            ->assertJsonPath('job.provider', 'mock');
        $this->get('/try-on-results/'.$jobId)->assertOk()->assertHeader('content-type', 'image/jpeg');
    }

    public function test_mirror_cannot_read_another_mirror_try_on_job(): void
    {
        config(['ai_tryon.provider' => 'mock']);

        [$tenant, $mirror, $token, $product] = $this->mirrorFixture();
        $otherMirror = Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => 'OTHER123',
            'api_token_hash' => hash('sha256', 'other-token'),
            'location_name' => 'Other',
            'status' => MirrorStatus::Paired,
        ]);
        $job = TryOnJob::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $tenant->id,
            'mirror_id' => $otherMirror->id,
            'product_id' => $product->id,
            'status' => TryOnJobStatus::Queued,
            'provider' => 'mock',
            'input_image_path' => 'try-on/inputs/example.jpg',
        ]);

        $this->withToken($token)->getJson('/api/mirror/try-on-jobs/'.$job->public_id)->assertNotFound();
    }

    public function test_job_failure_is_recorded_when_provider_is_not_configured(): void
    {
        Storage::fake('local');
        config([
            'filesystems.default' => 'local',
            'ai_tryon.provider' => 'nvidia',
            'ai_tryon.nvidia.api_key' => null,
            'ai_tryon.nvidia.model' => null,
        ]);

        [$tenant, $mirror, $token, $product] = $this->mirrorFixture();

        $response = $this->withToken($token)->post('/api/mirror/try-on-jobs', [
            'product_id' => $product->id,
            'snapshot' => UploadedFile::fake()->image('snapshot.jpg', 640, 480),
        ])->assertCreated();

        $this->assertDatabaseHas('try_on_jobs', [
            'public_id' => $response->json('job.id'),
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'status' => TryOnJobStatus::Failed->value,
        ]);
    }

    public function test_admin_lists_only_tenant_try_on_jobs(): void
    {
        [$tenant, $mirror, , $product] = $this->mirrorFixture();
        $other = Tenant::query()->create(['name' => 'Other', 'domain' => 'other.test', 'status' => TenantStatus::Active]);
        $user = User::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Admin',
            'email' => 'admin-'.Str::random(6).'@test.local',
            'password' => 'password',
            'role' => UserRole::Owner,
            'status' => UserStatus::Active,
        ]);
        $job = TryOnJob::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'product_id' => $product->id,
            'status' => TryOnJobStatus::Queued,
            'provider' => 'mock',
            'input_image_path' => 'try-on/inputs/a.jpg',
        ]);
        TryOnJob::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $other->id,
            'mirror_id' => Mirror::query()->create(['tenant_id' => $other->id, 'pairing_code' => 'OTHERTEN', 'location_name' => 'Other', 'status' => MirrorStatus::Pending])->id,
            'product_id' => Product::query()->create(['tenant_id' => $other->id, 'name' => 'Other Product', 'unit_price' => 1, 'currency' => 'EGP', 'status' => ProductStatus::Active])->id,
            'status' => TryOnJobStatus::Queued,
            'provider' => 'mock',
            'input_image_path' => 'try-on/inputs/b.jpg',
        ]);

        Sanctum::actingAs($user, ['admin']);

        $this->getJson('/api/admin/try-on-jobs')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.id', $job->public_id);
    }

    public function test_mirror_creates_and_reads_mock_try_on_batch(): void
    {
        Storage::fake('local');
        config(['filesystems.default' => 'local', 'ai_tryon.provider' => 'mock']);

        [$tenant, $mirror, $token, $product, $size] = $this->mirrorFixture();
        $second = Product::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Shirt',
            'unit_price' => 900,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
            'garment_type' => 'shirt',
        ]);

        $response = $this->withToken($token)->post('/api/mirror/try-on-batches', [
            'product_ids' => [$product->id, $second->id],
            'sizing_chart_id' => $size->id,
            'snapshot' => UploadedFile::fake()->image('snapshot.jpg', 640, 480),
        ])->assertCreated();

        $batchId = $response->json('batch.id');
        $this->assertDatabaseHas('try_on_batches', [
            'public_id' => $batchId,
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'status' => 'completed',
            'outfit_count' => 2,
        ]);
        $this->assertSame(2, TryOnJob::query()->whereHas('batch', fn ($query) => $query->where('public_id', $batchId))->count());

        $this->withToken($token)->getJson('/api/mirror/try-on-batches/'.$batchId)
            ->assertOk()
            ->assertJsonPath('batch.status', 'completed')
            ->assertJsonPath('batch.completed_count', 2)
            ->assertJsonCount(2, 'batch.jobs');
    }

    public function test_mirror_cannot_read_another_mirror_try_on_batch(): void
    {
        [$tenant, $mirror, $token] = $this->mirrorFixture();
        $otherMirror = Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => 'BATCH123',
            'api_token_hash' => hash('sha256', 'other-token'),
            'location_name' => 'Other',
            'status' => MirrorStatus::Paired,
        ]);
        $batch = TryOnBatch::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $tenant->id,
            'mirror_id' => $otherMirror->id,
            'status' => 'queued',
            'provider' => 'mock',
            'input_image_path' => 'try-on/batches/example/input.jpg',
        ]);

        $this->withToken($token)->getJson('/api/mirror/try-on-batches/'.$batch->public_id)->assertNotFound();
    }

    public function test_purge_deletes_expired_batch_media_and_jobs(): void
    {
        Storage::fake('local');
        config(['filesystems.default' => 'local']);

        [$tenant, $mirror, , $product] = $this->mirrorFixture();
        Storage::disk('local')->put('try-on/batches/old/input.jpg', 'input');
        Storage::disk('local')->put('try-on/results/old.jpg', 'result');

        $batch = TryOnBatch::query()->create([
            'public_id' => (string) Str::uuid(),
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'status' => 'completed',
            'provider' => 'mock',
            'input_image_path' => 'try-on/batches/old/input.jpg',
            'outfit_count' => 1,
            'completed_count' => 1,
            'expires_at' => now()->subMinute(),
        ]);
        TryOnJob::query()->create([
            'public_id' => (string) Str::uuid(),
            'try_on_batch_id' => $batch->id,
            'tenant_id' => $tenant->id,
            'mirror_id' => $mirror->id,
            'product_id' => $product->id,
            'status' => TryOnJobStatus::Completed,
            'provider' => 'mock',
            'input_image_path' => 'try-on/batches/old/input.jpg',
            'result_image_path' => 'try-on/results/old.jpg',
        ]);

        $this->artisan('tryon:purge-expired')->assertSuccessful();

        $this->assertDatabaseCount('try_on_batches', 0);
        $this->assertDatabaseCount('try_on_jobs', 0);
        Storage::disk('local')->assertMissing('try-on/batches/old/input.jpg');
        Storage::disk('local')->assertMissing('try-on/results/old.jpg');
    }

    private function mirrorFixture(): array
    {
        $tenant = Tenant::query()->create(['name' => 'Store', 'domain' => Str::random(8).'.test', 'status' => TenantStatus::Active]);
        $token = Str::random(64);
        $mirror = Mirror::query()->create([
            'tenant_id' => $tenant->id,
            'pairing_code' => strtoupper(Str::random(8)),
            'api_token_hash' => hash('sha256', $token),
            'location_name' => 'Room 1',
            'status' => MirrorStatus::Paired,
        ]);
        $product = Product::query()->create([
            'tenant_id' => $tenant->id,
            'name' => 'Jacket',
            'unit_price' => 1200,
            'currency' => 'EGP',
            'status' => ProductStatus::Active,
            'garment_type' => 'jacket',
        ]);
        $size = $product->sizingCharts()->create([
            'size_label' => 'L',
            'shoulder_width_cm' => 46,
            'chest_width_cm' => 54,
            'height_cm' => 72,
        ]);

        return [$tenant, $mirror, $token, $product, $size];
    }
}
