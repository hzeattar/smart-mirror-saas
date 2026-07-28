FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json ./
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader --no-scripts
COPY . .
RUN composer dump-autoload --no-dev --optimize && php artisan package:discover --ansi

FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY resources ./resources
COPY vite.config.js ./
COPY public ./public
RUN npm run build

FROM php:8.4-cli-alpine
RUN apk add --no-cache bash libpq-dev icu-dev libzip-dev oniguruma-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql pcntl intl zip bcmath
WORKDIR /app
COPY --from=vendor /app /app
COPY --from=frontend /app/public/build /app/public/build
RUN chmod +x scripts/start.sh \
    && chown -R www-data:www-data storage bootstrap/cache database public
USER www-data
EXPOSE 8080
CMD ["./scripts/start.sh"]
