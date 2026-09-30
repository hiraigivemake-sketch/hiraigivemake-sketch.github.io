<?php
/**
 * クリケア訪問看護ステーション
 * ホームページのフォーム受け取りプログラム（ロリポップ！に設置）
 *
 * 【できること】
 *   ・お問い合わせフォームと、見学申込＆応募フォームの両方を受け取ります
 *   ・事業所あてに内容をメールで送ります
 *   ・送信された方へ「受け付けました」の自動返信を送ります
 *   ・万一メールが届かなかったときのため、控えをサーバーにも保存します
 *
 * 【設置のしかた】
 *   このファイル1つを、ロリポップ！FTP で公開フォルダの中の
 *   「cricare」フォルダにアップロードするだけです。
 *   必要なフォルダやファイルは、初回の送信時に自動で作られます。
 *
 * 設定はすぐ下の「■ 設定」だけ直せば動きます。
 */

// ============================================================ ■ 設定
$CONFIG = array(

    // 通知を受け取るメールアドレス（複数書けます）
    'to' => array(
        'hirai@giveandmake-c.com',
    ),

    // 送信元として表示するアドレス
    // ※ giveandmake-c.com のアドレスにしてください（迷惑メール扱いを防ぐため）
    'from'      => 'hirai@giveandmake-c.com',
    'from_name' => 'クリケア訪問看護ステーション',

    // 送信された方へ自動返信を送るか
    'auto_reply' => true,

    // フォームを設置しているホームページのアドレス（ここ以外からの送信は受け付けません）
    'allowed_origins' => array(
        'https://giveandmake-c.com',
        'https://www.giveandmake-c.com',
        'https://hiraigivemake-sketch.github.io',
        'http://localhost:8000',
    ),

    // 送信後に戻るページ
    'thanks_url' => 'https://giveandmake-c.com/contact-thanks/',

    // 控えを保存するフォルダ（外から読めないように自動で保護されます）
    'log_dir' => __DIR__ . '/_data',
);

// ============================================================ 受け取る項目
// ラベルは、メールに表示される見出しです。
$FORMS = array(
    'contact' => array(
        'title'      => 'お問い合わせ',
        'thanks_url' => 'https://giveandmake-c.com/contact-thanks/',
        'fields'     => array(
            'name'    => array('label' => 'お名前',             'required' => true),
            'tel'     => array('label' => '電話番号',           'required' => true),
            'email'   => array('label' => 'メールアドレス',     'required' => true, 'type' => 'email'),
            'topic'   => array('label' => 'お問い合わせ項目',   'required' => true),
            'message' => array('label' => 'その他お問い合わせ内容', 'required' => false),
        ),
    ),
    'entry' => array(
        'title'      => '見学申込＆応募',
        'thanks_url' => 'https://giveandmake-c.com/entry-thanks/',
        'fields'     => array(
            'name'    => array('label' => 'お名前',   'required' => true),
            'email'   => array('label' => 'E-mail',   'required' => true, 'type' => 'email'),
            'job'     => array('label' => '希望求人', 'required' => true),
            'purpose' => array('label' => '希望内容', 'required' => true),
            'office'  => array('label' => '希望事業所', 'required' => true),
            'tel'     => array('label' => '電話番号', 'required' => false),
            'message' => array('label' => 'その他ご相談やご質問', 'required' => false),
        ),
    ),
);

// ============================================================ ここから下は編集不要
mb_language('uni');
mb_internal_encoding('UTF-8');
date_default_timezone_set('Asia/Tokyo');

header('Content-Type: text/plain; charset=UTF-8');

// --- 送信元ページの確認（別サイトからの悪用を防ぐ）-------------------
$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
if ($origin !== '' && in_array($origin, $CONFIG['allowed_origins'], true)) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Vary: Origin');
}

// ブラウザからの事前確認（OPTIONS）にはすぐ返す
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo 'このページは直接開けません。';
    exit;
}

// --- どちらのフォームか -------------------------------------------
$form_id = isset($_POST['_form']) ? trim($_POST['_form']) : '';
if (!isset($FORMS[$form_id])) {
    fail(400, 'フォームの種類が分かりませんでした。');
}
$form = $FORMS[$form_id];

// --- 迷惑送信よけ -------------------------------------------------
// ① 人には見えない欄。自動プログラムだけが入力してしまう
if (!empty($_POST['_check'])) {
    ok($form, '送信しました。');   // 迷惑送信には成功を装って何もしない
}
// ② 表示から送信までが極端に速い場合も自動プログラムとみなす
//    ※ お使いのパソコンの時計がずれていると、経過時間がマイナスになることがあります。
//      その場合は判定せず、通常どおり受け付けます（お問い合わせを失わないため）。
$started = isset($_POST['_t']) ? (int)$_POST['_t'] : 0;
if ($started > 0) {
    $elapsed = time() - $started;
    if ($elapsed >= 0 && $elapsed < 3) {
        ok($form, '送信しました。');
    }
}

// --- 入力内容の取り出しと確認 --------------------------------------
$values = array();
$errors = array();

foreach ($form['fields'] as $key => $def) {
    $raw = isset($_POST[$key]) ? $_POST[$key] : '';
    if (!is_string($raw)) { $raw = ''; }

    $value = trim(str_replace(array("\r\n", "\r"), "\n", $raw));
    if (mb_strlen($value) > 5000) {
        $value = mb_substr($value, 0, 5000);
    }

    if (!empty($def['required']) && $value === '') {
        $errors[] = $def['label'] . 'を入力してください。';
    }
    if ($value !== '' && isset($def['type']) && $def['type'] === 'email'
        && !filter_var($value, FILTER_VALIDATE_EMAIL)) {
        $errors[] = $def['label'] . 'の形式が正しくありません。';
    }
    $values[$key] = $value;
}

if ($errors) {
    fail(422, implode("\n", $errors));
}

// --- メールの本文を組み立てる --------------------------------------
$lines = array();
foreach ($form['fields'] as $key => $def) {
    $lines[] = '■ ' . $def['label'];
    $lines[] = ($values[$key] !== '' ? $values[$key] : '（未入力）');
    $lines[] = '';
}
$content = implode("\n", $lines);

$meta = "─────────────\n"
      . '受信日時: ' . date('Y/m/d H:i') . "\n"
      . '送信元: ' . safe(isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '不明') . "\n";

// --- 控えをサーバーに保存（メールが届かなかったときの保険）-----------
save_log($CONFIG['log_dir'], $form_id, $content . $meta);

// --- 事業所あてに送る ----------------------------------------------
$visitor_email = isset($values['email']) ? $values['email'] : '';
$visitor_name  = isset($values['name']) ? $values['name'] : '';

$headers  = 'From: ' . mb_encode_mimeheader($CONFIG['from_name'], 'UTF-8')
          . ' <' . safe($CONFIG['from']) . '>' . "\r\n";
if ($visitor_email !== '') {
    $headers .= 'Reply-To: ' . safe($visitor_email) . "\r\n";
}

$sent = false;
foreach ($CONFIG['to'] as $to) {
    $subject = '【ホームページ】' . $form['title'] . ' に新しい送信がありました';
    if (mb_send_mail(safe($to), $subject, $content . $meta, $headers, '-f' . safe($CONFIG['from']))) {
        $sent = true;
    }
}

// --- 送信された方へ自動返信 ----------------------------------------
if ($CONFIG['auto_reply'] && $visitor_email !== '') {
    $reply_subject = '【クリケア訪問看護ステーション】' . $form['title'] . 'を受け付けました';
    $reply_body =
        ($visitor_name !== '' ? $visitor_name . ' 様' . "\n\n" : '') .
        "この度はご連絡いただき、誠にありがとうございます。\n" .
        "以下の内容で承りました。担当者より改めてご連絡いたしますので、少々お待ちください。\n" .
        "\n" .
        "※このメールは自動送信です。ご返信いただいても対応いたしかねます。\n" .
        "\n" .
        "─────────────────────\n" .
        $content .
        "─────────────────────\n" .
        "\n" .
        "クリケア訪問看護ステーション\n" .
        "株式会社GIVE&MAKE\n" .
        "〒639-0231 奈良県香芝市下田西2-278-7 香芝ビル2F\n" .
        "TEL 0745-76-5825 / FAX 0745-76-5826\n" .
        "営業時間 9:00〜18:00\n" .
        "https://giveandmake-c.com\n";

    $reply_headers = 'From: ' . mb_encode_mimeheader($CONFIG['from_name'], 'UTF-8')
                   . ' <' . safe($CONFIG['from']) . '>' . "\r\n";
    @mb_send_mail(safe($visitor_email), $reply_subject, $reply_body, $reply_headers, '-f' . safe($CONFIG['from']));
}

if (!$sent) {
    // 控えは保存してあるので、内容が失われることはありません
    fail(500, '送信処理でエラーが発生しました。お手数ですが、お電話（0745-76-5825）でご連絡ください。');
}

ok($form, '送信しました。');


// ============================================================ 小さな道具
/** メールヘッダに使う値から、改行などの危険な文字を取り除く */
function safe($v) {
    return trim(str_replace(array("\r", "\n", "%0a", "%0d"), '', (string)$v));
}

/** JavaScript から送られたか（＝画面を移動させずに返事をする）*/
function is_ajax() {
    return isset($_POST['_ajax']) && $_POST['_ajax'] === '1';
}

/** 成功したときの返事 */
function ok($form, $message) {
    if (is_ajax()) {
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode(array('ok' => true, 'message' => $message), JSON_UNESCAPED_UNICODE);
    } else {
        header('Location: ' . $form['thanks_url'], true, 303);
    }
    exit;
}

/** 失敗したときの返事 */
function fail($code, $message) {
    http_response_code($code);
    if (is_ajax()) {
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode(array('ok' => false, 'error' => $message), JSON_UNESCAPED_UNICODE);
    } else {
        header('Content-Type: text/html; charset=UTF-8');
        echo '<!doctype html><meta charset="utf-8"><title>送信できませんでした</title>'
           . '<div style="font-family:sans-serif;max-width:40em;margin:4em auto;line-height:1.9">'
           . '<h1 style="font-size:1.3em">送信できませんでした</h1><p>'
           . nl2br(htmlspecialchars($message, ENT_QUOTES, 'UTF-8'))
           . '</p><p><a href="javascript:history.back()">前のページに戻る</a></p></div>';
    }
    exit;
}

/** 控えをファイルに残す
 *
 * 控えには個人情報が含まれるため、外から読まれないようにしてあります。
 * ファイルの拡張子を .php にし、先頭に exit を書いておくことで、
 * ブラウザで直接開かれても中身は一切表示されません。
 * （.htaccess を別途置く必要はありません）
 */
function save_log($dir, $form_id, $text) {
    if (!is_dir($dir)) {
        @mkdir($dir, 0700, true);
    }
    if (!is_dir($dir)) { return; }

    // フォルダの中身が一覧表示されないようにする
    $index = $dir . '/index.php';
    if (!file_exists($index)) {
        @file_put_contents($index, "<?php exit; ?>\n");
    }

    $file = $dir . '/' . $form_id . '-' . date('Y-m') . '.php';
    if (!file_exists($file)) {
        @file_put_contents($file, "<?php exit; /* ここから下は送信内容の控えです */ ?>\n");
    }
    $entry = str_repeat('=', 50) . "\n" . date('Y/m/d H:i:s') . "\n" . $text . "\n";
    @file_put_contents($file, $entry, FILE_APPEND | LOCK_EX);
}
