<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Mirror;
use App\Models\MirrorSessionEvent;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MirrorSessionEventController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'events' => ['required', 'array', 'min:1', 'max:50'],
            'events.*.event' => ['required', 'string', 'max:80'],
            'events.*.ts' => ['nullable', 'date'],
            'events.*.fps' => ['nullable', 'numeric', 'min:0', 'max:240'],
            'events.*.payload' => ['nullable', 'array'],
        ]);

        /** @var Mirror $mirror */
        $mirror = $request->attributes->get('mirror');
        $rows = collect($data['events'])->map(fn (array $event) => [
            'tenant_id' => $mirror->tenant_id,
            'mirror_id' => $mirror->id,
            'event' => $event['event'],
            'fps' => $event['fps'] ?? ($event['payload']['fps'] ?? null),
            'payload' => json_encode($event['payload'] ?? collect($event)->except(['event', 'ts', 'fps'])->all(), JSON_THROW_ON_ERROR),
            'occurred_at' => isset($event['ts']) ? date('Y-m-d H:i:s', strtotime((string) $event['ts'])) : now(),
            'created_at' => now(),
            'updated_at' => now(),
        ])->all();

        MirrorSessionEvent::query()->insert($rows);

        $latest = collect($data['events'])->last();
        $metadata = $mirror->metadata ?? [];
        $metadata['session_health'] = [
            'last_event' => $latest['event'] ?? null,
            'last_fps' => $latest['fps'] ?? ($latest['payload']['fps'] ?? null),
            'last_event_at' => now()->toIso8601String(),
        ];
        $mirror->update(['metadata' => $metadata]);

        return response()->json(['accepted' => count($rows)]);
    }
}
