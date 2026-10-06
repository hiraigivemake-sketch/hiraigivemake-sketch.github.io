// ===========================================================================
// 業務ハブ の設定ファイル
//
// このファイルを書き換えるだけで、ボタン・行き先・検索の言葉を増やせます。
// 書き換えたら ⑥ 変更をGitHubに送る で公開されます（数分で反映）。
//
// 【行き先（destinations）の書き方】
//   {
//     app: "slack",                  … どのアプリか（下の apps の名前）
//     label: "業務連絡",              … ボタンに出る名前
//     url: "https://…",              … 開く先。空 "" のときはアプリのトップへ
//     keywords: ["連絡", "れんらく"], … 検索で引っかかる言葉（いくつでも）
//     categories: ["internal"],      … どのトップボタンに出すか（複数可）
//     note: "補足"                    … ボタンの下に小さく出る説明（省略可）
//   },
//
// 【各アプリのリンクの取り方】
//   Slack   : チャンネル名を右クリック →「リンクをコピー」。
//             未設定のときは「チャンネル名で開く」仕組みで動くので、
//             まずは label と同じチャンネル名なら url は空でも構いません。
//   Drive   : フォルダを開いて、上のアドレス欄をコピー（…/folders/xxxx）。
//             未設定のときはフォルダ名で Drive を検索した結果が開きます。
//   ZEST・S-QUE : ログイン後に出る画面のアドレスをコピー。
// ===========================================================================

window.HUB_CONFIG = {

  title: "クリケア 業務ハブ",
  subtitle: "やりたいことを選ぶか、言葉で探してください",

  // ---- アプリ一覧（色とトップページ） ------------------------------------
  apps: {
    slack: {
      name: "Slack",
      color: "#4A154B",
      home: "https://app.slack.com/",
      // チャンネル名だけで開ける仕組み。url が空の行き先はこれを使う。
      byName: function (label) {
        return "https://slack.com/app_redirect?channel=" + encodeURIComponent(label);
      },
    },
    lineworks: {
      name: "LINE WORKS",
      color: "#00C300",
      home: "https://talk.worksmobile.com/",
    },
    line: {
      name: "公式LINE",
      color: "#06C755",
      home: "https://chat.line.biz/",
    },
    drive: {
      name: "Google Drive",
      color: "#1E8E3E",
      home: "https://drive.google.com/",
      // フォルダ名で Drive を検索する。url が空の行き先はこれを使う。
      byName: function (label) {
        return "https://drive.google.com/drive/search?q=" + encodeURIComponent(label);
      },
    },
    zest: {
      name: "ZEST",
      color: "#E8541E",
      home: "https://homecare.zest.jp/login",
    },
    sque: {
      name: "S-QUE",
      color: "#1F6FB2",
      home: "https://s-que.net/s-quekaigo/login/index.html",
    },
  },

  // ---- トップボタン（並び順のとおりに表示） -------------------------------
  categories: [
    { id: "internal", label: "事業所内の連絡", icon: "💬",
      keywords: ["連絡", "れんらく", "共有", "報告", "社内", "事業所内", "ないぶ", "内部"] },
    { id: "docs",     label: "書類管理", sub: "事務的業務", icon: "📁",
      keywords: ["書類", "しょるい", "文書", "ファイル", "資料", "事務", "じむ", "保存", "ドライブ"] },
    { id: "schedule", label: "スケジュール確認", icon: "📅",
      keywords: ["スケジュール", "すけじゅーる", "シフト", "しふと", "予定", "よてい", "訪問予定", "勤務", "カレンダー"] },
    { id: "learning", label: "学習", icon: "📚",
      keywords: ["学習", "がくしゅう", "勉強", "べんきょう", "研修", "けんしゅう", "eラーニング", "イーラーニング", "講座", "テスト", "受講"] },
    { id: "external", label: "外部との連絡・連携", icon: "🤝",
      keywords: ["外部", "がいぶ", "連携", "れんけい", "ケアマネ", "病院", "主治医", "家族", "利用者さんと", "お客様"] },
  ],

  // ---- 行き先一覧 --------------------------------------------------------
  destinations: [

    // Slack ---------------------------------------------------------------
    { app: "slack", label: "業務連絡", url: "",
      keywords: ["業務連絡", "業務", "連絡", "お知らせ", "周知"],
      categories: ["internal"] },

    { app: "slack", label: "利用者の情報共有", url: "",
      keywords: ["利用者", "りようしゃ", "情報共有", "共有", "状態", "様子", "申し送り", "申送り"],
      categories: ["internal"] },

    { app: "slack", label: "管理者報告", url: "",
      keywords: ["管理者", "かんりしゃ", "報告", "ほうこく", "上司", "所長", "管理者に"],
      categories: ["internal"] },

    { app: "slack", label: "スケジュール管理", url: "",
      keywords: ["スケジュール", "シフト", "予定", "変更", "休み", "休暇", "交代"],
      categories: ["internal", "schedule"] },

    { app: "slack", label: "事務業務", url: "",
      keywords: ["事務", "じむ", "請求", "せいきゅう", "レセプト", "経理", "書類"],
      categories: ["internal", "docs"] },

    // LINE WORKS ----------------------------------------------------------
    { app: "lineworks", label: "LINE WORKS", url: "",
      keywords: ["ラインワークス", "らいんわーくす", "lineworks", "line works", "ワークス", "トーク", "ケアマネ", "連携", "外部"],
      categories: ["internal", "external"],
      note: "トーク一覧を開きます" },

    // 公式LINE ------------------------------------------------------------
    { app: "line", label: "公式LINE チャット", url: "https://chat.line.biz/",
      keywords: ["公式line", "公式ライン", "こうしきらいん", "ライン", "らいん", "line", "チャット", "返信", "利用者さんと", "家族", "問い合わせ"],
      categories: ["external"],
      note: "利用者・ご家族とのやり取り" },

    { app: "line", label: "公式LINE 管理画面", url: "https://manager.line.biz/",
      keywords: ["公式line", "公式ライン", "管理画面", "一斉送信", "配信", "メッセージ配信", "友だち"],
      categories: ["external"],
      note: "一斉配信・設定" },

    // Google Drive --------------------------------------------------------
    { app: "drive", label: "顧客管理", url: "",
      keywords: ["顧客", "こきゃく", "利用者", "台帳", "名簿", "契約", "契約書", "顧客管理"],
      categories: ["docs"] },

    { app: "drive", label: "業務書類", url: "",
      keywords: ["業務書類", "書類", "様式", "テンプレ", "雛形", "ひながた", "マニュアル", "規程", "報告書"],
      categories: ["docs"] },

    { app: "drive", label: "Drive トップ", url: "https://drive.google.com/",
      keywords: ["ドライブ", "どらいぶ", "drive", "google", "グーグル", "ファイル", "保存"],
      categories: ["docs"],
      note: "すべてのフォルダ" },

    // ZEST ----------------------------------------------------------------
    { app: "zest", label: "ZEST（訪問スケジュール）", url: "https://homecare.zest.jp/login",
      keywords: ["zest", "ぜすと", "ゼスト", "訪問", "ほうもん", "訪問予定", "訪問スケジュール", "ルート", "シフト", "予定表", "今日の訪問", "明日の訪問"],
      categories: ["schedule"],
      note: "訪問予定・シフトの確認" },

    // S-QUE ---------------------------------------------------------------
    { app: "sque", label: "S-QUE（e-learning）", url: "https://s-que.net/s-quekaigo/login/index.html",
      keywords: ["sque", "s-que", "エスキュー", "えすきゅー", "研修", "学習", "勉強", "eラーニング", "動画", "受講", "テスト"],
      categories: ["learning"],
      note: "研修・学習" },
  ],
};
