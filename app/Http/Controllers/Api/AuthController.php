<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Schema;
use Illuminate\Validation\ValidationException;
use Throwable;

class AuthController extends Controller
{
    public function login(Request $request): JsonResponse
    {
        $data = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required', 'string'],
            'device_name' => ['nullable', 'string', 'max:100'],
        ]);

        try {
            if (! Schema::hasTable('users') || ! Schema::hasTable('personal_access_tokens')) {
                Log::error('Authentication tables are missing.', [
                    'connection' => config('database.default'),
                    'users_table' => Schema::hasTable('users'),
                    'tokens_table' => Schema::hasTable('personal_access_tokens'),
                ]);

                return response()->json([
                    'message' => 'Authentication database is not ready. Please wait for the deployment to finish.',
                    'code' => 'AUTH_DATABASE_NOT_READY',
                ], 503);
            }

            $user = User::query()->with('tenant')->where('email', $data['email'])->first();

            if (! $user || ! Hash::check($data['password'], $user->password)) {
                throw ValidationException::withMessages([
                    'email' => ['The provided credentials are incorrect.'],
                ]);
            }

            if (! $user->tenant) {
                Log::error('Authenticated user has no tenant.', ['user_id' => $user->id]);

                return response()->json([
                    'message' => 'Your store account is not linked to a tenant.',
                    'code' => 'AUTH_TENANT_MISSING',
                ], 503);
            }

            $token = $user
                ->createToken($data['device_name'] ?? 'admin-dashboard', ['admin'])
                ->plainTextToken;

            return response()->json([
                'token' => $token,
                'user' => $this->present($user),
            ]);
        } catch (ValidationException $exception) {
            throw $exception;
        } catch (Throwable $exception) {
            Log::error('Authentication backend failure.', [
                'exception' => $exception::class,
                'message' => $exception->getMessage(),
                'connection' => config('database.default'),
            ]);

            return response()->json([
                'message' => 'Authentication service is temporarily unavailable. Please retry after the deployment completes.',
                'code' => 'AUTH_BACKEND_FAILURE',
            ], 503);
        }
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json([
            'user' => $this->present($request->user()->load('tenant')),
        ]);
    }

    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()?->delete();

        return response()->json(['message' => 'Logged out.']);
    }

    private function present(User $user): array
    {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'role' => $user->role->value,
            'tenant' => [
                'id' => $user->tenant->id,
                'name' => $user->tenant->name,
                'domain' => $user->tenant->domain,
            ],
        ];
    }
}
