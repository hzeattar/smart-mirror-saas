<?php

namespace App\Enums;

enum BackgroundRemovalStatus: string
{
    case NotRequested = 'not_requested';
    case Pending = 'pending';
    case Processing = 'processing';
    case Completed = 'completed';
    case Failed = 'failed';
}
