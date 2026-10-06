/**
 * クリケア 業務ハブ ── 新着メッセージの「受け口」（Google Apps Script）
 *
 * Slack と 公式LINE に新しいメッセージが届いたことを業務ハブ（/hub/）に知らせるための
 * 小さなプログラムです。メッセージの本文や送った人の名前は一切保存しません。
 * 保存するのは「どのチャンネル（またはLINE）に、いつ最後のメッセージが来たか」だけです。
 *
 * ─────────────────────────────────────────────────────────────
 * 【設定手順】（30分ほど。一度やれば終わりです）
 *
 * A. このスクリプトを置く
 *   1. https://script.google.com/ を開く（Googleにログインした状態で）
 *   2. 「新しいプロジェクト」→ 最初のコードを全部消して、このファイルの中身を貼り付け → 保存
 *   3. 左の歯車「プロジェクトの設定」→ 下の「スクリプト プロパティ」で次を追加
 *        HUB_KEY        … 好きな英数字（例：kuricare2026）。業務ハブ側にも同じものを書きます
 *        LINE_KEY       … 好きな英数字（LINE の受け口の合言葉。HUB_KEY と別のもの）
 *        SLACK_TOKEN    … 手順B で取る xoxb- で始まる文字列
 *        SLACK_CHANNELS … 手順B で取る「チャンネルID:ボタンの名前」をカンマ区切りで
 *                          例：C0123ABCD:業務連絡,C0456EFGH:利用者の情報共有
 *                          （名前は hub/config.js の label と同じにしてください）
 *   4. 右上「デプロイ」→「新しいデプロイ」→ 種類「ウェブアプリ」
 *        次のユーザーとして実行：自分 ／ アクセスできるユーザー：全員
 *      →「デプロイ」→ 出てきた「ウェブアプリのURL」（…/exec で終わる）を控える
 *   5. 上の関数の選択で「setup」を選んで「▶ 実行」（初回は許可を求められるので許可）
 *      → 1分ごとに Slack を見に行く設定が入ります
 *
 * B. Slack 側（無料版で可）
 *   1. https://api.slack.com/apps →「Create New App」→「From scratch」
 *      名前は「業務ハブ」など、ワークスペースは自分のもの
 *   2. 左「OAuth & Permissions」→ Bot Token Scopes に次を追加
 *        channels:history ／ channels:read ／ groups:history ／ groups:read
 *   3. 同じ画面の上「Install to Workspace」→ 許可 → 「Bot User OAuth Token」(xoxb-…) をコピー
 *      → 手順A-3 の SLACK_TOKEN に貼る
 *   4. Slack で知らせたい各チャンネルを開き、メッセージ欄に  /invite @業務ハブ  と送る
 *   5. 各チャンネルのIDを調べる：チャンネル名をクリック → 一番下に「チャンネルID: C…」
 *      → 手順A-3 の SLACK_CHANNELS に書く
 *
 * C. 公式LINE 側
 *   1. https://manager.line.biz/ → 対象アカウント → 設定 → Messaging API → 「Messaging APIを利用する」
 *      （すでに有効なら不要）
 *   2. https://developers.line.biz/console/ → そのチャネル → Messaging API設定 →
 *        Webhook URL に  手順A-4 のURL + ?k=LINE_KEYの値  を入れる
 *        例：https://script.google.com/macros/s/xxxxx/exec?k=abcd1234
 *        「Webhookの利用」をオン
 *      ※「検証」ボタンはエラー表示になることがありますが、実際の通知は届きます
 *   3. 公式LINEの管理画面 → 設定 → 応答設定 → 「Webhook」がオンになっていることを確認
 *      （チャット機能はそのまま使えます）
 *
 * D. 業務ハブ側
 *   hub/config.js の notify に、手順A-4 のURL と HUB_KEY を書いて公開（⑥ 変更をGitHubに送る）
 *
 * 動作確認：ブラウザで  手順A-4のURL + ?key=HUB_KEYの値  を開くと
 *   {"now":…, "slack":{…}, "line":{…}} のような文字が出れば成功です。
 * ─────────────────────────────────────────────────────────────
 */

var PROP = PropertiesService.getScriptProperties();

/** 最初に1回だけ手で実行：1分ごとに Slack を確認する設定を作る */
function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'pollSlack') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('pollSlack').timeBased().everyMinutes(1).create();
  pollSlack();
  Logger.log('設定完了。1分ごとに Slack を確認します。');
}

// ---- 保存（本文は保存しない。最後のメッセージの時刻だけ） ----------------
function loadState() {
  try { return JSON.parse(PROP.getProperty('STATE') || '{}'); } catch (e) { return {}; }
}
function withState(fn) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var s = loadState();
    fn(s);
    PROP.setProperty('STATE', JSON.stringify(s));
  } finally {
    lock.releaseLock();
  }
}

// ---- Slack：1分ごとに各チャンネルの最新メッセージの時刻を確認 -----------
function pollSlack() {
  var token = PROP.getProperty('SLACK_TOKEN');
  var list = PROP.getProperty('SLACK_CHANNELS') || '';
  if (!token || !list) return;

  var results = {};
  list.split(',').forEach(function (item) {
    var parts = item.split(':');
    var id = (parts[0] || '').trim();
    var label = (parts[1] || id).trim();
    if (!id) return;
    var url = 'https://slack.com/api/conversations.history?channel=' + encodeURIComponent(id) + '&limit=5';
    var res = UrlFetchApp.fetch(url, { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
    var j = {};
    try { j = JSON.parse(res.getContentText()); } catch (e) {}
    if (!j.ok) { results[label] = { error: j.error || 'http_' + res.getResponseCode() }; return; }
    // 人が書いたメッセージだけ（参加・退出などのお知らせは除く）
    var msgs = (j.messages || []).filter(function (m) { return !m.subtype || m.subtype === 'thread_broadcast'; });
    results[label] = msgs.length ? { at: Math.floor(parseFloat(msgs[0].ts) * 1000) } : { at: 0 };
  });

  withState(function (s) {
    s.slack = s.slack || {};
    Object.keys(results).forEach(function (label) {
      var prev = s.slack[label] || {};
      var cur = results[label];
      if (cur.error) { prev.error = cur.error; }
      else { delete prev.error; if (cur.at > (prev.at || 0)) prev.at = cur.at; }
      s.slack[label] = prev;
    });
  });
}

// ---- 公式LINE：メッセージが届くと LINE がここに知らせてくる --------------
function doPost(e) {
  var key = PROP.getProperty('LINE_KEY');
  if (key && ((e.parameter || {}).k || '') !== key) {
    return ContentService.createTextOutput('forbidden');
  }
  var body = {};
  try { body = JSON.parse((e.postData && e.postData.contents) || '{}'); } catch (err) {}
  var latest = 0;
  (body.events || []).forEach(function (ev) {
    if (ev.type === 'message' && ev.timestamp > latest) latest = ev.timestamp;
  });
  if (latest) {
    withState(function (s) {
      s.line = s.line || {};
      if (latest > (s.line.at || 0)) s.line.at = latest;
    });
  }
  return ContentService.createTextOutput('ok');
}

// ---- 業務ハブがここを読みに来る ---------------------------------------
function doGet(e) {
  var key = PROP.getProperty('HUB_KEY');
  if (key && ((e.parameter || {}).key || '') !== key) {
    return json({ error: 'forbidden' });
  }
  var s = loadState();
  return json({ now: Date.now(), slack: s.slack || {}, line: s.line || {} });
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
