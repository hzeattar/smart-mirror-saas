<?php

namespace App\Enums;

enum MirrorStatus: string
{
    case Pending = 'pending';
    case Paired = 'paired';
    case Online = 'online';
    case Offline = 'offline';
    case Disabled = 'disabled';
}
