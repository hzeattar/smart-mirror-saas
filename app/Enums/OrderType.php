<?php

namespace App\Enums;

enum OrderType: string
{
    case InStore = 'in_store';
    case Delivery = 'delivery';
}
