/**
 * クリケア訪問看護ステーション
 * お問い合わせフォーム・見学申込＆応募フォームを自動で作るスクリプト
 *
 * 【使い方】
 *   1. https://script.google.com/ を開く（Googleにログインした状態で）
 *   2. 「新しいプロジェクト」を押す
 *   3. 最初から書かれているコードをすべて消して、このファイルの中身を貼り付ける
 *   4. 上の「▶ 実行」を押す（初回は許可を求められるので「許可」を押す）
 *   5. 下に出る「実行ログ」をすべてコピーして、Claude Code に貼り付ける
 *
 * これだけで、2つのフォームと回答用スプレッドシート、
 * 新着通知メールの設定まで、すべて自動でできあがります。
 */

// 新しいお問い合わせが来たときに知らせるメールアドレス
var NOTIFY_EMAIL = Session.getActiveUser().getEmail();

// 送信された方へ「受け付けました」の自動返信を送るか（true = 送る）
var SEND_AUTO_REPLY = true;

// 自動返信メールの文面（自由に書き換えてください）
var AUTO_REPLY_SUBJECT = '【クリケア訪問看護ステーション】お問い合わせを受け付けました';
var AUTO_REPLY_BODY =
  'この度はお問い合わせいただき、誠にありがとうございます。\n' +
  '以下の内容で承りました。担当者より改めてご連絡いたしますので、少々お待ちください。\n' +
  '\n' +
  '※このメールは自動送信です。ご返信いただいても対応いたしかねます。\n' +
  '\n' +
  '─────────────────────\n' +
  '{{CONTENT}}' +
  '─────────────────────\n' +
  '\n' +
  'クリケア訪問看護ステーション\n' +
  '株式会社GIVE&MAKE\n' +
  '〒639-0231 奈良県香芝市下田西2-278-7 香芝ビル2F\n' +
  'TEL 0745-76-5825 / FAX 0745-76-5826\n' +
  '営業時間 9:00〜18:00\n' +
  'https://giveandmake-c.com\n';

// ────────────────────────────────────────────────────────────
// これを実行してください
// ────────────────────────────────────────────────────────────
function createForms() {
  var out = [];
  out.push('════════════════════════════════════════');
  out.push(' クリケア フォーム作成結果');
  out.push(' 以下をすべてコピーして Claude Code に貼り付けてください');
  out.push('════════════════════════════════════════');

  out = out.concat(buildContactForm());
  out.push('');
  out = out.concat(buildEntryForm());

  out.push('');
  out.push('════════════════════════════════════════');
  out.push(' 通知先メールアドレス: ' + NOTIFY_EMAIL);
  out.push('════════════════════════════════════════');

  Logger.log(out.join('\n'));
}

// ────────────────────────────────────────────────────────────
// ① お問い合わせフォーム
// ────────────────────────────────────────────────────────────
function buildContactForm() {
  var form = FormApp.create('クリケア訪問看護ステーション｜お問い合わせ');
  form.setDescription(
    '訪問看護のご依頼・ご相談はこちらからお問い合わせください。\n' +
    'クリケア訪問看護ステーション（奈良県香芝市）'
  );
  openToEveryone(form);

  var items = {};
  items.name = form.addTextItem()
    .setTitle('お名前').setHelpText('例：山田 花子').setRequired(true);
  items.tel = form.addTextItem()
    .setTitle('電話番号').setHelpText('例：000-1234-5678').setRequired(true);
  items.email = form.addTextItem()
    .setTitle('メールアドレス').setHelpText('例：abc@mail.com').setRequired(true);
  items.topic = form.addMultipleChoiceItem()
    .setTitle('お問い合わせ項目')
    .setChoiceValues([
      '相談したい',
      '訪問看護をお願いしたい',
      'その他（内容を次の欄にご記入ください）'
    ])
    .setRequired(true);
  items.message = form.addParagraphTextItem()
    .setTitle('その他お問い合わせ内容')
    .setHelpText('その他ご相談やご質問をこちらへご入力ください')
    .setRequired(false);

  form.setConfirmationMessage(
    'お問い合わせありがとうございました。\n担当者より折り返しご連絡いたします。'
  );

  linkSpreadsheet(form, 'クリケア｜お問い合わせ 回答');
  setNotification(form);

  return report('お問い合わせフォーム', form, items, {
    name: 'name', tel: 'tel', email: 'email', topic: 'topic', message: 'message'
  });
}

// ────────────────────────────────────────────────────────────
// ② 見学申込＆応募フォーム
// ────────────────────────────────────────────────────────────
function buildEntryForm() {
  var form = FormApp.create('クリケア訪問看護ステーション｜見学申込＆応募');
  form.setDescription(
    '見学のお申し込み・採用へのご応募はこちらからお願いいたします。\n' +
    'クリケア訪問看護ステーション（奈良県香芝市）'
  );
  openToEveryone(form);

  var items = {};
  items.name = form.addTextItem()
    .setTitle('お名前').setRequired(true);
  items.email = form.addTextItem()
    .setTitle('E-mail').setRequired(true);
  items.job = form.addListItem()
    .setTitle('希望求人')
    .setChoiceValues([
      '[正社員] 看護師',
      '[パート]看護師',
      '[正社員] 理学療法士',
      '[正社員]医療事務',
      '[正社員]主任ケアマネジャー',
      '※選考希望以外の方'
    ])
    .setRequired(true);
  items.purpose = form.addListItem()
    .setTitle('希望内容')
    .setChoiceValues([
      '面接希望',
      '見学・面談のみ希望',
      '見学面談＋同行訪問希望',
      'その他ご相談やご質問'
    ])
    .setRequired(true);
  items.office = form.addListItem()
    .setTitle('希望事業所')
    .setChoiceValues([
      'クリケア訪問看護ステーション',
      'クリケア訪問看護ステーション斑鳩事業所（仮称）'
    ])
    .setRequired(true);
  items.tel = form.addTextItem()
    .setTitle('電話番号').setHelpText('※ハイフン(-)不要').setRequired(false);
  items.message = form.addParagraphTextItem()
    .setTitle('その他ご相談やご質問').setRequired(false);

  form.setConfirmationMessage(
    'お申し込みありがとうございました。\n担当者より折り返しご連絡いたします。'
  );

  linkSpreadsheet(form, 'クリケア｜見学申込＆応募 回答');
  setNotification(form);

  return report('見学申込＆応募フォーム', form, items, {
    name: 'name', email: 'email', job: 'job', purpose: 'purpose',
    office: 'office', tel: 'tel', message: 'message'
  });
}

// ────────────────────────────────────────────────────────────
// 以下は共通の処理（さわる必要はありません）
// ────────────────────────────────────────────────────────────

/** 誰でも回答できるようにする（ログイン不要・1人1回の制限なし） */
function openToEveryone(form) {
  try { form.setRequireLogin(false); } catch (e) {}   // 個人アカウントでは不要
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setProgressBar(false);
}

/** 回答をスプレッドシートに貯める */
function linkSpreadsheet(form, name) {
  var ss = SpreadsheetApp.create(name);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
}

/** 新着があったらメールで知らせる */
function setNotification(form) {
  var id = form.getId();
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'notifyNewResponse' && t.getTriggerSourceId() === id) {
      ScriptApp.deleteTrigger(t);   // 二重登録を防ぐ
    }
  });
  ScriptApp.newTrigger('notifyNewResponse').forForm(form).onFormSubmit().create();
}

/** 通知メールの中身（自動で呼ばれます） */
function notifyNewResponse(e) {
  var form = e.source;
  var lines = [];
  var visitorEmail = '';

  e.response.getItemResponses().forEach(function (ir) {
    var title = ir.getItem().getTitle();
    var value = String(ir.getResponse() || '（未入力）');
    lines.push('■ ' + title);
    lines.push(value);
    lines.push('');
    if (/mail/i.test(title) && value.indexOf('@') > 0) visitorEmail = value.trim();
  });
  var content = lines.join('\n');

  // ① 事業所への通知
  try {
    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: '【ホームページ】' + form.getTitle() + ' に新しい送信がありました',
      body: content +
        '─────────────\n' +
        '受信日時: ' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm') + '\n' +
        '回答一覧: ' + form.getEditUrl()
    });
  } catch (err) {
    console.error('通知メールの送信に失敗: ' + err);
  }

  // ② 送信された方への自動返信
  if (SEND_AUTO_REPLY && visitorEmail) {
    try {
      MailApp.sendEmail({
        to: visitorEmail,
        subject: AUTO_REPLY_SUBJECT,
        body: AUTO_REPLY_BODY.replace('{{CONTENT}}', content),
        name: 'クリケア訪問看護ステーション'
      });
    } catch (err) {
      console.error('自動返信の送信に失敗: ' + err);
    }
  }
}

/** ホームページ側の設定に必要な情報を書き出す */
function report(label, form, items, keyMap) {
  // 仮の回答を作ると、項目ごとの受付番号（entry.xxxxx）が分かる
  var resp = form.createResponse();
  var order = [];
  for (var key in keyMap) {
    var item = items[key];
    var typed;
    var t = item.getType();
    if (t === FormApp.ItemType.MULTIPLE_CHOICE) {
      typed = item.asMultipleChoiceItem().createResponse(item.asMultipleChoiceItem().getChoices()[0].getValue());
    } else if (t === FormApp.ItemType.LIST) {
      typed = item.asListItem().createResponse(item.asListItem().getChoices()[0].getValue());
    } else if (t === FormApp.ItemType.PARAGRAPH_TEXT) {
      typed = item.asParagraphTextItem().createResponse('__' + key + '__');
    } else {
      typed = item.asTextItem().createResponse('__' + key + '__');
    }
    resp = resp.withItemResponse(typed);
    order.push(key);
  }

  var prefilled = resp.toPrefilledUrl();
  var action = form.getPublishedUrl().replace('/viewform', '/formResponse');

  var out = [];
  out.push('────────────────────────────────────────');
  out.push('【' + label + '】');
  out.push('  公開URL   : ' + form.getPublishedUrl());
  out.push('  送信先URL : ' + action);
  out.push('  編集URL   : ' + form.getEditUrl());
  out.push('  項目の受付番号:');

  // prefilled の中から entry.xxxxx を項目順に拾う
  var entries = prefilled.match(/entry\.\d+/g) || [];
  var seen = {};
  var uniq = [];
  entries.forEach(function (x) { if (!seen[x]) { seen[x] = 1; uniq.push(x); } });

  for (var i = 0; i < order.length; i++) {
    out.push('    ' + pad(order[i]) + ' : ' + (uniq[i] || '(取得できず)'));
  }
  out.push('  （確認用の下書きURL: ' + prefilled + ' ）');
  return out;
}

function pad(s) {
  while (s.length < 8) s += ' ';
  return s;
}
