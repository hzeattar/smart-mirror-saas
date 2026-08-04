<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Models\MirrorSessionEvent;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;

class MirrorSessionEventController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        if (! $request->has('events') && $request->filled('event')) {
            $request->merge([
                'events' => [[
                    'event' => $request->input('event'),
                    'ts' => $request->input('ts'),
                    'fps' => $request->input('fps'),
                    'session_id' => $request->input('session_id'),
                    'sequence' => $request->input('sequence'),
                    'severity' => $request->input('severity'),
                    'payload' => $request->input('payload', []),
                ]],
            ]);
        }

        $data = $request->validate([
            'session_id' => ['nullable', 'string', 'max:80'],
            'events' => ['required', 'array', 'min:1', 'max:50'],
            'events.*.event' => ['required', 'string', 'max:80'],
            'events.*.ts' => ['nullable'],
            'events.*.fps' => ['nullable', 'numeric', 'min:0', 'max:240'],
            'events.*.session_id' => ['nullable', 'string', 'max:80'],
            'events.*.sequence' => ['nullable', 'integer', 'min:0'],
            'events.*.severity' => ['nullable', 'string', 'max:20'],
            'events.*.payload' => ['nullable', 'array'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $rows = collect($data['events'])->map(fn (array $event) => [
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'session_id' => $event['session_id'] ?? $data['session_id'] ?? null,
            'sequence' => $event['sequence'] ?? null,
            'severity' => $this->severity($event['severity'] ?? null),
            'event' => $event['event'],
            'fps' => $event['fps'] ?? ($event['payload']['fps'] ?? null),
            'payload' => json_encode($event['payload'] ?? collect($event)->except(['event', 'ts', 'fps', 'session_id', 'sequence', 'severity'])->all(), JSON_THROW_ON_ERROR),
            'occurred_at' => $this->occurredAt($event['ts'] ?? null),
            'created_at' => now(),
            'updated_at' => now(),
        ])->all();

        MirrorSessionEvent::query()->insert($rows);

        $metadata = $mirror->metadata ?? [];
        $previousHealth = is_array($metadata['session_health'] ?? null) ? $metadata['session_health'] : [];
        $events = collect($data['events']);
        $latest = $events->last();
        $latestFpsEvent = $events->reverse()->first(fn (array $event) => isset($event['fps']) || isset($event['payload']['fps']));
        $metadata['session_health'] = [
            'last_event' => $latest['event'] ?? null,
            'last_fps' => $latestFpsEvent['fps'] ?? ($latestFpsEvent['payload']['fps'] ?? ($previousHealth['last_fps'] ?? null)),
            'last_event_at' => now()->toIso8601String(),
            'session_id' => $latest['session_id'] ?? $data['session_id'] ?? null,
            'sequence' => $latest['sequence'] ?? null,
            'severity' => $this->severity($latest['severity'] ?? null),
            'payload' => $latest['payload'] ?? null,
        ];
        $mirror->update(['metadata' => $metadata]);

        return response()->json(['accepted' => count($rows)]);
    }

    private function occurredAt(mixed $value): Carbon
    {
        if ($value === null || $value === '') {
            return now();
        }

        try {
            if (is_numeric($value)) {
                return Carbon::createFromTimestamp((float) $value);
            }

            return Carbon::parse((string) $value);
        } catch (\Throwable) {
            return now();
        }
    }

    private function severity(?string $value): string
    {
        $severity = strtolower((string) ($value ?: 'info'));

        return in_array($severity, ['debug', 'info', 'warning', 'error', 'critical'], true) ? $severity : 'info';
    }
}
