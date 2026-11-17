<?php
declare(strict_types=1);
require __DIR__ . '/_runtime.php';
try {
    $cfg = wm_config();
    if (!wm_authorized($cfg['contact'] ?? [])) wm_fail(503, 'Das Kontaktformular ist derzeit nicht verfügbar.');
    if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
        wm_form($cfg, 'contact', 'Kontakt', '<p><label>Name <input name="name" required maxlength="100" autocomplete="name"></label></p><p><label>E-Mail <input type="email" name="email" required maxlength="254" autocomplete="email"></label></p><p><label>Nachricht <textarea name="message" required maxlength="5000"></textarea></label></p>'); exit;
    }
    $nonce = wm_post($cfg, 'contact');
    if (array_diff(array_keys($_POST), ['csrf','website','name','email','message'])) wm_fail(422, 'Unbekannte Formularfelder.');
    $name = wm_field('name', 100); $email = wm_email(wm_field('email', 254)); $message = wm_field('message', 10000);
    if (preg_match('/[\r\n]/', $name)) wm_fail(422, 'Bitte einen gültigen Namen eingeben.');
    wm_rate($cfg, $nonce, 'contact');
    wm_deliver($cfg, 'contact', (string)($cfg['contact']['to'] ?? ''), $email, 'Website-Anfrage', "Name: $name\nE-Mail: $email\n\n$message");
    wm_fail(202, 'Ihre Anfrage wurde entgegengenommen.');
} catch (Throwable $error) { wm_fail(503, 'Die Anfrage konnte nicht bestätigt werden. Bitte nicht mehrfach absenden und bei Bedarf einen anderen Kontaktweg nutzen.'); }
