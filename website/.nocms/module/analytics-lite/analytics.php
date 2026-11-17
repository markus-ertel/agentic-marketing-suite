<?php
declare(strict_types=1);
require __DIR__ . '/_runtime.php';
try {
    $cfg = wm_config();
    if (PHP_SAPI === 'cli') {
        if (($argv[1] ?? '') !== '--export') throw new RuntimeException('Use --export');
        $path = $cfg['_data'] . '/analytics.json';
        if (is_link($path)) throw new RuntimeException('Invalid analytics file');
        $state = is_file($path) ? json_decode(file_get_contents($path), true, 32, JSON_THROW_ON_ERROR) : [];
        $out = fopen('php://stdout', 'wb'); fputcsv($out, ['date','page','pageviews']);
        foreach ($state as $day => $pages) foreach ($pages as $page => $count) fputcsv($out, [$day, wm_csv_cell((string)$page), $count]);
        exit;
    }
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') wm_fail(405, 'Nur POST erlaubt.');
    wm_origin($cfg);
    if (!wm_authorized($cfg['analytics'] ?? []) || ($_SERVER['HTTP_DNT'] ?? '') === '1' || ($_SERVER['HTTP_SEC_GPC'] ?? '') === '1') { http_response_code(204); exit; }
    if (!ctype_digit($_SERVER['CONTENT_LENGTH'] ?? '') || (int)$_SERVER['CONTENT_LENGTH'] > 512) wm_fail(413, 'Anfrage zu groß.');
    $input = json_decode(file_get_contents('php://input', false, null, 0, 513), true, 4, JSON_THROW_ON_ERROR);
    if (!is_array($input) || array_keys($input) !== ['page'] || !is_string($input['page'])) wm_fail(422, 'Ungültige Seite.');
    $pages = $cfg['analytics']['pages'] ?? [];
    if (!is_array($pages) || count($pages) > 1000 || !in_array($input['page'], $pages, true) || !preg_match('#^/(?!/)[A-Za-z0-9/._~%-]*$#D', $input['page']) || str_contains($input['page'], '..')) wm_fail(422, 'Unbekannte Seite.');
    $retention = $cfg['analytics']['retention_days'] ?? 30;
    if (!is_int($retention) || $retention < 1 || $retention > 365) throw new RuntimeException('Invalid retention');
    // Optional (L4): a per-visitor daily cap needs a short-lived pseudonym; off by default to store nothing per visitor.
    $perClient = $cfg['analytics']['max_hits_per_client_day'] ?? null;
    if ($perClient !== null && (!is_int($perClient) || $perClient < 1 || $perClient > 10000)) throw new RuntimeException('Invalid client limit');
    if ($perClient !== null && !wm_analytics_allowed($cfg, $perClient)) { header('Cache-Control: no-store'); http_response_code(204); exit; }
    $today = gmdate('Y-m-d'); $cutoff = gmdate('Y-m-d', time() - ($retention - 1) * 86400); $page = $input['page'];
    wm_store($cfg, 'analytics', function(array &$state) use ($today,$cutoff,$page): void {
        $state = array_filter($state, fn($day) => $day >= $cutoff && $day <= $today, ARRAY_FILTER_USE_KEY);
        if (array_sum($state[$today] ?? []) >= 100000) return;
        $state[$today][$page] = ($state[$today][$page] ?? 0) + 1;
    });
    header('Cache-Control: no-store'); http_response_code(204);
} catch (Throwable $error) { if (PHP_SAPI === 'cli') { fwrite(STDERR, "ANALYTICS_EXPORT_BLOCKED\n"); exit(2); } wm_fail(503, 'Messung derzeit nicht verfügbar.'); }
