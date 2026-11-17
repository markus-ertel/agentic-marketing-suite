<?php
declare(strict_types=1);
ini_set('display_errors', '0');
/* Standalone PHP 8.3+ helpers. No Suite or agent service is required on the webhost. */
function wm_fail(int $status, string $message): never {
    http_response_code($status); header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store'); header('X-Content-Type-Options: nosniff');
    echo $message; exit;
}
function wm_inside(string $path, string $root): bool { return $path === $root || str_starts_with($path, $root . DIRECTORY_SEPARATOR); }
function wm_config(): array {
    $path = realpath((string)getenv('WEBMODULE_CONFIG'));
    $documentRoot = (string)($_SERVER['DOCUMENT_ROOT'] ?? '');
    if ($documentRoot === '') $documentRoot = (string)getenv('WEBMODULE_DOCUMENT_ROOT');
    $root = $documentRoot !== '' ? realpath($documentRoot) : false;
    if (!$root || !$path || wm_inside($path, $root) || !is_file($path) || filesize($path) > 65536) throw new RuntimeException('Private configuration required');
    $cfg = json_decode(file_get_contents($path), true, 32, JSON_THROW_ON_ERROR);
    $data = realpath((string)($cfg['data_dir'] ?? ''));
    if (!$data || !is_dir($data) || !is_writable($data) || wm_inside($data, $root)) throw new RuntimeException('Private storage required');
    $origin = $cfg['origin'] ?? '';
    $url = is_string($origin) ? parse_url($origin) : false;
    if (!$url || (isset($url['user']) || isset($url['pass'])) || isset($url['query']) || isset($url['fragment']) || !empty($url['path']) || !isset($url['host'])) throw new RuntimeException('Invalid origin');
    if (($url['scheme'] ?? '') !== 'https' && !(($url['scheme'] ?? '') === 'http' && in_array($url['host'], ['localhost','127.0.0.1','[::1]'], true))) throw new RuntimeException('HTTPS required');
    if (!is_string($cfg['privacy_url'] ?? null) || !str_starts_with($cfg['privacy_url'], '/') || str_starts_with($cfg['privacy_url'], '//') || preg_match('/[\\\\\x00-\x20]/', $cfg['privacy_url'])) throw new RuntimeException('Privacy URL required');
    $proxies = $cfg['trusted_proxies'] ?? [];
    if (!is_array($proxies) || count($proxies) > 50) throw new RuntimeException('Invalid trusted_proxies');
    foreach ($proxies as $proxy) if (!is_string($proxy) || filter_var($proxy, FILTER_VALIDATE_IP) === false) throw new RuntimeException('Invalid trusted_proxies');
    $cfg['_data'] = $data; return $cfg;
}
/* Real visitor address. Behind a reverse proxy/CDN every request comes from the proxy; only then, and only for
   configured proxy addresses, the rightmost untrusted X-Forwarded-For entry is the visitor (L10). */
function wm_client_ip(array $cfg): string {
    $remote = (string)($_SERVER['REMOTE_ADDR'] ?? '');
    $proxies = $cfg['trusted_proxies'] ?? [];
    if (!in_array($remote, $proxies, true)) return $remote;
    $chain = array_map('trim', explode(',', (string)($_SERVER['HTTP_X_FORWARDED_FOR'] ?? '')));
    for ($i = count($chain) - 1; $i >= 0; $i--) {
        $candidate = $chain[$i];
        if (filter_var($candidate, FILTER_VALIDATE_IP) === false) return $remote;
        if (!in_array($candidate, $proxies, true)) return $candidate;
    }
    return $remote;
}
function wm_secret(): string {
    $secret = (string)getenv('WEBMODULE_SECRET');
    if (strlen($secret) < 32) throw new RuntimeException('Server secret required');
    return $secret;
}
function wm_escape(string $value): string { return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function wm_origin(array $cfg): void {
    if (($_SERVER['HTTP_ORIGIN'] ?? '') !== $cfg['origin']) wm_fail(403, 'Anfrage von dieser Herkunft nicht erlaubt.');
}
function wm_token(array $cfg, string $purpose): string {
    $payload = time() . '.' . bin2hex(random_bytes(16));
    $binding = $purpose . '|' . $payload . '|' . wm_client_ip($cfg);
    return $payload . '.' . hash_hmac('sha256', $binding, wm_secret());
}
function wm_verify_token(array $cfg, string $purpose, mixed $token): string {
    if (!is_string($token) || !preg_match('/^([0-9]{10})\.([a-f0-9]{32})\.([a-f0-9]{64})$/D', $token, $parts)) wm_fail(403, 'Formular bitte erneut öffnen.');
    $age = time() - (int)$parts[1];
    $binding = $purpose . '|' . $parts[1] . '.' . $parts[2] . '|' . wm_client_ip($cfg);
    if ($age < 0 || $age > 900 || !hash_equals(hash_hmac('sha256', $binding, wm_secret()), $parts[3])) wm_fail(403, 'Formular bitte erneut öffnen.');
    return hash('sha256', $token);
}
function wm_store(array $cfg, string $name, callable $change): mixed {
    if (!preg_match('/^[a-z-]+$/D', $name)) throw new RuntimeException('Invalid store');
    umask(0077); $base = $cfg['_data'] . '/' . $name;
    if (is_link($base . '.lock') || is_link($base . '.json')) throw new RuntimeException('Symlinked store');
    $lock = fopen($base . '.lock', 'c');
    if (!$lock || !flock($lock, LOCK_EX)) throw new RuntimeException('Storage locked');
    $temporary = null;
    try {
        $state = is_file($base . '.json') ? json_decode(file_get_contents($base . '.json'), true, 64, JSON_THROW_ON_ERROR) : [];
        if (!is_array($state)) throw new RuntimeException('Invalid storage');
        $result = $change($state);
        $temporary = tempnam($cfg['_data'], '.store-');
        if ($temporary === false) throw new RuntimeException('Storage unavailable');
        chmod($temporary, 0600); $file = fopen($temporary, 'wb');
        $data = json_encode($state, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
        if (!$file || fwrite($file, $data) !== strlen($data)) throw new RuntimeException('Storage write failed');
        fflush($file); if (function_exists('fsync')) fsync($file); fclose($file);
        if (!rename($temporary, $base . '.json')) throw new RuntimeException('Storage commit failed');
        return $result;
    } finally { if ($temporary && is_file($temporary)) unlink($temporary); flock($lock, LOCK_UN); fclose($lock); }
}
function wm_rate(array $cfg, string $nonce, string $purpose): void {
    $ip = wm_client_ip($cfg);
    // Separate quotas per form (L4): newsletter traffic cannot exhaust the contact form and vice versa.
    $form = preg_replace('/[^a-z-]/', '', $purpose);
    $accepted = wm_store($cfg, 'rate', function(array &$state) use ($nonce, $ip, $form): bool {
        $now = time();
        $state = array_filter($state, fn($entry) => is_array($entry) && ($entry['expires'] ?? 0) > $now);
        $seen = 'nonce-' . $nonce;
        if (isset($state[$seen])) return false;
        $client = hash_hmac('sha256', date('Y-m-d') . '|' . $ip, wm_secret());
        $limits = ['minute-' . $form . '-' . $client . '-' . intdiv($now,60) => [60,3], 'hour-' . $form . '-' . $client . '-' . intdiv($now,3600) => [3600,10], 'global-' . $form . '-' . intdiv($now,3600) => [3600,100]];
        foreach ($limits as $key => [$window,$limit]) if (($state[$key]['count'] ?? 0) >= $limit) return false;
        foreach ($limits as $key => [$window,$limit]) $state[$key] = ['count' => ($state[$key]['count'] ?? 0) + 1, 'expires' => $now + $window];
        $state[$seen] = ['count' => 1, 'expires' => $now + 900]; return true;
    });
    if (!$accepted) wm_fail(429, 'Zu viele Anfragen. Bitte später erneut versuchen und das Formular neu öffnen.');
}
function wm_post(array $cfg, string $purpose): string {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') wm_fail(405, 'Nur POST erlaubt.');
    wm_origin($cfg);
    $length = filter_var($_SERVER['CONTENT_LENGTH'] ?? '', FILTER_VALIDATE_INT);
    if ($length === false || $length <= 0 || $length > 16384) wm_fail(413, 'Nachricht ist zu groß.');
    if (!is_string($_POST['website'] ?? '') || ($_POST['website'] ?? '') !== '') wm_fail(400, 'Formular konnte nicht verarbeitet werden.');
    return wm_verify_token($cfg, $purpose, $_POST['csrf'] ?? null);
}
function wm_field(string $name, int $max): string {
    $value = $_POST[$name] ?? '';
    if (!is_string($value) || !wm_valid_utf8($value) || strlen($value) > $max || trim($value) === '' || str_contains($value, "\0")) wm_fail(422, 'Bitte alle Felder korrekt ausfüllen.');
    return trim($value);
}
function wm_valid_utf8(string $value): bool { return preg_match('//u', $value) === 1; }
function wm_email(string $value): string {
    if (preg_match('/[\r\n\x00]/', $value) || !filter_var($value, FILTER_VALIDATE_EMAIL) || strlen($value) > 254) wm_fail(422, 'Bitte eine gültige E-Mail-Adresse eingeben.');
    return $value;
}
function wm_authorized(array $section): bool {
    $permission = $section['authorization'] ?? [];
    $expiry = $permission['expires_at'] ?? '';
    $expires = is_string($expiry) && preg_match('/T.*(?:Z|[+-][0-9]{2}:[0-9]{2})$/D', $expiry) ? strtotime($expiry) : false;
    return ($section['enabled'] ?? false) === true && is_string($permission['approval_ref'] ?? null) && trim($permission['approval_ref']) !== '' && $expires !== false && $expires > time();
}
function wm_event(array $cfg, array $event): void {
    umask(0077); $path = $cfg['_data'] . '/delivery-events.jsonl';
    if (is_link($path)) throw new RuntimeException('Symlinked event log');
    $file = fopen($path, 'ab');
    if (!$file || !flock($file, LOCK_EX)) throw new RuntimeException('Audit unavailable');
    try { $data = json_encode($event, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE) . "\n"; if (fwrite($file, $data) !== strlen($data)) throw new RuntimeException('Audit write failed'); fflush($file); if (function_exists('fsync')) fsync($file); }
    finally { flock($file, LOCK_UN); fclose($file); }
}
function wm_deliver(array $cfg, string $kind, string $to, string $reply, string $subject, string $body): string {
    $section = $cfg[$kind] ?? [];
    $from = wm_email((string)($section['from'] ?? ''));
    wm_email($to); if ($reply !== '') wm_email($reply);
    $transport = $section['transport'] ?? 'outbox';
    $id = bin2hex(random_bytes(16));
    $event = ['id' => $id, 'kind' => $kind, 'recorded_at' => gmdate('c'), 'status' => 'started'];
    if (!wm_authorized($section)) throw new RuntimeException('Service mandate missing or expired');
    $event['authorization_ref'] = $section['authorization']['approval_ref'];
    $event['policy_sha256'] = hash('sha256', json_encode($section, JSON_THROW_ON_ERROR));
    wm_event($cfg, $event);
    try {
        if ($transport === 'outbox') {
            $message = ['schema_version' => '0.1', 'id' => $id, 'kind' => $kind, 'channel' => 'email', 'to' => $to, 'from' => $from, 'reply_to' => $reply, 'subject' => $subject, 'body' => $body, 'created_at' => gmdate('c'), 'untrusted_input' => true, 'status' => 'queued'];
            umask(0077); $path = $cfg['_data'] . '/inbound-' . $id . '.json'; $file = fopen($path, 'x');
            $encoded = json_encode($message, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
            if (!$file || fwrite($file, $encoded) !== strlen($encoded)) throw new RuntimeException('Outbox unavailable');
            fflush($file); if (function_exists('fsync')) fsync($file); fclose($file); $status = 'queued';
        } elseif ($transport === 'mail') {
            $headers = ['From' => $from, 'Content-Type' => 'text/plain; charset=UTF-8'];
            if ($reply !== '') $headers['Reply-To'] = $reply;
            $status = mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, $headers) ? 'accepted' : 'failed';
        } else throw new RuntimeException('Unsupported transport');
    } catch (Throwable $error) { wm_event($cfg, array_replace($event, ['status' => 'uncertain', 'recorded_at' => gmdate('c')])); throw $error; }
    wm_event($cfg, array_replace($event, ['status' => $status, 'recorded_at' => gmdate('c')]));
    if ($status === 'failed') throw new RuntimeException('Mail was not accepted');
    return $status;
}
function wm_form(array $cfg, string $purpose, string $heading, string $fields): void {
    header('Content-Type: text/html; charset=utf-8'); header('Cache-Control: no-store');
    header("Content-Security-Policy: default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'self'");
    header('X-Content-Type-Options: nosniff'); header('Referrer-Policy: no-referrer');
    echo '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' . wm_escape($heading) . '</title><main><h1>' . wm_escape($heading) . '</h1><form method="post"><input type="hidden" name="csrf" value="' . wm_escape(wm_token($cfg, $purpose)) . '">' . $fields . '<div hidden aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div><p><a href="' . wm_escape($cfg['privacy_url']) . '">Datenschutzhinweise</a></p><button type="submit">Bestätigen</button></form></main></html>';
}

/* Analytics hits per visitor and day (L4): a single client cannot inflate counts beyond this. */
function wm_analytics_allowed(array $cfg, int $limit): bool {
    $ip = wm_client_ip($cfg);
    return wm_store($cfg, 'rate', function(array &$state) use ($ip, $limit): bool {
        $now = time();
        $state = array_filter($state, fn($entry) => is_array($entry) && ($entry['expires'] ?? 0) > $now);
        $key = 'analytics-' . hash_hmac('sha256', gmdate('Y-m-d') . '|' . $ip, wm_secret());
        if (($state[$key]['count'] ?? 0) >= $limit) return false;
        $state[$key] = ['count' => ($state[$key]['count'] ?? 0) + 1, 'expires' => $now + 86400]; return true;
    });
}
/* CSV exports are opened in spreadsheets; never let stored text run as a formula (L2). */
function wm_csv_cell(mixed $value): mixed {
    if (is_string($value) && $value !== '' && (str_contains("=@\t\r", $value[0]) || (($value[0] === '+' || $value[0] === '-') && strlen($value) > 1 && !ctype_digit($value[1]) && !str_contains(' .,', $value[1])))) return "'" . $value;
    return $value;
}
