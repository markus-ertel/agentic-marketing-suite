<?php
declare(strict_types=1);
require __DIR__ . '/_runtime.php';
function nl_manage_token(string $id): string { return $id . '.' . hash_hmac('sha256', 'unsubscribe|' . $id, wm_secret()); }
function nl_confirm_page(array $cfg, string $action, string $token): void {
    wm_form($cfg, 'newsletter-' . $action, $action === 'confirm' ? 'Newsletter-Anmeldung bestätigen' : 'Newsletter abmelden', '<input type="hidden" name="action" value="' . wm_escape($action) . '"><input type="hidden" name="token" value="' . wm_escape($token) . '"><p>' . ($action === 'confirm' ? 'Bitte bestätigen Sie Ihre eigene Anmeldung.' : 'Bitte bestätigen Sie die Abmeldung.') . '</p>');
}
try {
    $cfg = wm_config();
    if (PHP_SAPI === 'cli') {
        if (($argv[1] ?? '') !== '--export-confirmed') throw new RuntimeException('Use --export-confirmed');
        $path = $cfg['_data'] . '/newsletter.json';
        if (is_link($path)) throw new RuntimeException('Invalid store');
        $records = is_file($path) ? json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR) : [];
        $out = fopen('php://stdout', 'wb'); fputcsv($out, ['id','email','consent_version','confirmed_at','unsubscribe_url']);
        foreach ($records as $id => $entry) if (($entry['state'] ?? '') === 'confirmed') fputcsv($out, array_map('wm_csv_cell', [$id,$entry['email'],$entry['consent_version'],$entry['confirmed_at'],$cfg['origin'] . ($cfg['newsletter']['endpoint_path'] ?? '/api/newsletter.php') . '?unsubscribe=' . nl_manage_token($id)]));
        exit;
    }
    if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
        foreach (['confirm','unsubscribe'] as $action) if (isset($_GET[$action])) {
            if (!is_string($_GET[$action]) || strlen($_GET[$action]) > 120) wm_fail(400, 'Ungültiger Link.');
            // GET never subscribes or unsubscribes: mail scanners cannot confirm consent.
            nl_confirm_page($cfg, $action, $_GET[$action]); exit;
        }
        if (!wm_authorized($cfg['newsletter'] ?? [])) wm_fail(503, 'Newsletter-Anmeldung derzeit nicht verfügbar.');
        $text = $cfg['newsletter']['consent_text'] ?? '';
        if (!is_string($text) || trim($text) === '') throw new RuntimeException('Consent wording required');
        wm_form($cfg, 'newsletter-signup', 'Newsletter anmelden', '<input type="hidden" name="action" value="signup"><p><label>E-Mail <input type="email" name="email" required maxlength="254" autocomplete="email"></label></p><p><label><input type="checkbox" name="consent" value="yes" required> ' . wm_escape($text) . '</label></p>'); exit;
    }
    $action = $_POST['action'] ?? '';
    if (!is_string($action) || !in_array($action, ['signup','confirm','unsubscribe'], true)) wm_fail(422, 'Ungültige Aktion.');
    $nonce = wm_post($cfg, 'newsletter-' . $action);
    if (array_diff(array_keys($_POST), ['csrf','website','action','token','email','consent'])) wm_fail(422, 'Unbekannte Felder.');
    if ($action === 'signup') {
        if (!wm_authorized($cfg['newsletter'] ?? [])) wm_fail(503, 'Newsletter-Anmeldung derzeit nicht verfügbar.');
        $email = wm_email(wm_field('email', 254));
        if (($_POST['consent'] ?? '') !== 'yes') wm_fail(422, 'Bitte die Einwilligung bestätigen.');
        $text = $cfg['newsletter']['consent_text'] ?? ''; $version = $cfg['newsletter']['consent_version'] ?? '';
        if (!is_string($text) || trim($text) === '' || !is_string($version) || trim($version) === '') throw new RuntimeException('Versioned consent required');
        wm_rate($cfg, $nonce, 'newsletter-signup'); $token = bin2hex(random_bytes(32)); $id = bin2hex(random_bytes(16));
        $created = wm_store($cfg, 'newsletter', function(array &$state) use ($email,$token,$id,$text,$version): bool {
            $now = time();
            foreach ($state as $key => $entry) {
                if (($entry['state'] ?? '') === 'pending' && ($entry['expires'] ?? 0) < $now) { unset($state[$key]); continue; }
                if (strtolower($entry['email'] ?? '') === strtolower($email) && in_array($entry['state'], ['pending','confirmed'], true)) return false;
            }
            $state[$id] = ['email'=>$email,'state'=>'pending','token_hash'=>hash('sha256',$token),'created_at'=>gmdate('c'),'expires'=>$now+86400,'consent_text'=>$text,'consent_version'=>$version,'events'=>[['type'=>'requested','at'=>gmdate('c')]]]; return true;
        });
        if ($created) {
            $url = $cfg['origin'] . (string)($cfg['newsletter']['endpoint_path'] ?? '/api/newsletter.php') . '?confirm=' . rawurlencode($token);
            if (!preg_match('#^/[A-Za-z0-9/._-]+\.php$#D', (string)($cfg['newsletter']['endpoint_path'] ?? '/api/newsletter.php'))) throw new RuntimeException('Invalid newsletter endpoint');
            wm_deliver($cfg, 'newsletter', $email, '', 'Newsletter-Anmeldung bestätigen', "Sie haben einen Newsletter angefordert.\nBitte öffnen Sie den Link und bestätigen Sie die Anmeldung ausdrücklich auf der Seite:\n$url\n\nOhne Bestätigung erfolgt keine Anmeldung. Der Link läuft nach 24 Stunden ab.");
        }
        wm_fail(202, 'Falls diese Adresse neu angemeldet werden kann, wurde die Bestätigungsanfrage entgegengenommen. Ohne ausdrückliche Bestätigung erfolgt keine Anmeldung.');
    }
    $token = wm_field('token', 120); if ($action !== 'unsubscribe') wm_rate($cfg, $nonce, 'newsletter-' . $action);
    $result = wm_store($cfg, 'newsletter', function(array &$state) use ($action,$token): array {
        if ($action === 'confirm') {
            foreach ($state as $id => &$entry) {
                if (($entry['state'] ?? '') === 'pending' && ($entry['expires'] ?? 0) >= time() && hash_equals($entry['token_hash'], hash('sha256', $token))) {
                    $entry['state'] = 'confirmed'; $entry['confirmed_at'] = gmdate('c');
                    unset($entry['token_hash'], $entry['expires']);
                    $entry['events'][] = ['type'=>'confirmed','at'=>$entry['confirmed_at']];
                    return ['ok'=>true,'id'=>$id];
                }
            }
        } elseif (preg_match('/^([a-f0-9]{32})\.([a-f0-9]{64})$/D', $token, $parts) && hash_equals(nl_manage_token($parts[1]), $token)) {
            $id = $parts[1];
            if (isset($state[$id])) {
                if ($state[$id]['state'] !== 'unsubscribed') {
                    $state[$id]['state'] = 'unsubscribed'; $state[$id]['unsubscribed_at'] = gmdate('c');
                    $state[$id]['events'][] = ['type'=>'unsubscribed','at'=>$state[$id]['unsubscribed_at']];
                }
                return ['ok'=>true,'id'=>$id];
            }
        }
        return ['ok'=>false];
    });
    if (!$result['ok']) wm_fail(422, 'Der Link ist ungültig, abgelaufen oder bereits verwendet.');
    wm_event($cfg, ['id'=>$result['id'],'kind'=>'newsletter-consent','recorded_at'=>gmdate('c'),'status'=>$action === 'confirm' ? 'confirmed' : 'unsubscribed']);
    if ($action === 'confirm') {
        header('Content-Type: text/html; charset=utf-8'); header('Cache-Control: no-store'); header('Referrer-Policy: no-referrer');
        echo '<!doctype html><html lang="de"><meta charset="utf-8"><title>Anmeldung bestätigt</title><p>Ihre Anmeldung wurde bestätigt.</p><a href="?unsubscribe=' . wm_escape(nl_manage_token($result['id'])) . '">Newsletter abmelden</a></html>'; exit;
    }
    wm_fail(200, 'Die Abmeldung wurde gespeichert.');
} catch (Throwable $error) { if (PHP_SAPI === 'cli') { fwrite(STDERR, "NEWSLETTER_EXPORT_BLOCKED\n"); exit(2); } wm_fail(503, 'Die Anfrage konnte nicht bestätigt werden. Bitte nicht mehrfach absenden und bei Bedarf einen anderen Kontaktweg nutzen.'); }
