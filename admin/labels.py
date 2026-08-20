#!/usr/bin/env python3
"""管理画面で使う日本語ラベル。ここを増やせば表示名が変わります。"""

# 画像として扱う項目名（サムネイル表示＋画像選択ボタンが出る）
IMAGE_KEYS = {
    "image", "images", "photo", "photos", "illustration", "thumbnail",
    "cover", "logo", "logo_footer", "favicon", "og_image", "icon",
}

# 長文として扱う項目名（大きな入力欄になる）
LONG_KEYS = {
    "text", "body_md", "description", "summary", "a", "answer",
    "text_html", "subtitle_html", "title_html", "catch", "value",
    "caption",
}

# 編集画面に出さない項目
HIDDEN_KEYS = {"_comment", "template", "slug", "url_pattern"}

# 大きなまとまり（ページ内のセクション）の名前
SECTION_LABELS = {
    "home_bottom": "ホーム下部の表示（ブログ・インスタグラム）",
    "posts": "インスタグラムの投稿",
    "hero": "メインビジュアル（一番上の大きな部分）",
    "notice": "お知らせ帯（オレンジの横長バナー）",
    "service": "「Service」セクション",
    "staff": "「Staff」セクション",
    "recruit": "「Recruitment」セクション",
    "company": "「Company」セクション",
    "philosophy": "理念",
    "message": "代表挨拶",
    "info": "会社情報の表",
    "books": "書籍紹介",
    "featured": "メインで紹介する書籍",
    "groups": "共著の書籍",
    "features": "特徴・写真つきカード",
    "areas": "訪問エリア",
    "tokutei": "特定行為についての説明",
    "blocks": "説明の各項目",
    "members": "スタッフ",
    "campaign": "キャンペーンの帯",
    "awesome": "クリケアのここが凄い！",
    "inside_view": "従業員目線で見たクリケア",
    "access": "アクセスマップ",
    "job_description": "業務内容",
    "daily_schedule": "1日の働き方例",
    "benefits": "福利厚生",
    "data": "数字で見る",
    "survey": "見学面談アンケート",
    "faq": "よくある質問",
    "jobs": "募集一覧の見出し",
    "fields": "フォームの入力項目",
    "google_form": "フォームの送信先設定",
    "head_actions": "ページ上部のボタン",
    "items": "項目",
    "rows": "表の行",
    "people": "人物",
    "company_info": "会社情報",
    "cta": "全ページ共通の案内欄",
    "nav": "ヘッダーのメニュー",
    "footer_nav": "フッターのメニュー",
    "social": "SNS・外部リンク",
    "contact": "お問い合わせ側",
    "entry": "採用応募側",
    "entries": "Googleフォームの項目ID",
}

# ひとつひとつの入力欄の名前
FIELD_LABELS = {
    "show_blog": "ブログ欄を表示する",
    "show_instagram": "インスタグラム欄を表示する",
    "instagram_first": "インスタグラムをブログより上に置く",
    "instagram_count": "インスタグラムを何件並べるか",
    "caption": "説明文（写真の下に2行まで出ます）",
    "post_url": "投稿のリンク先（https://www.instagram.com/p/... ）",
    "title": "見出し",
    "title_en": "英語の見出し",
    "title_html": "見出し（改行できます）",
    "label": "小見出し（日本語）",
    "seo_title": "検索結果に出るタイトル",
    "description": "検索結果に出る説明文",
    "text": "本文",
    "text_html": "本文（改行できます）",
    "subtitle_html": "サブ見出し（改行できます）",
    "body_md": "本文",
    "catch": "キャッチコピー",
    "lead": "リード文（小さい文字）",
    "summary": "要点（太字で出ます）",
    "heading": "見出し",
    "question": "質問",
    "q": "質問",
    "a": "回答",
    "voices": "スタッフの声（1行に1件）",
    "note": "補足",
    "credits": "著者・出版社（1行に1件）",
    "routes": "アクセス経路（1行に1件）",
    "options": "選択肢（1行に1件）",
    "image": "画像",
    "images": "画像",
    "photo": "写真",
    "photos": "写真",
    "illustration": "イラスト",
    "thumbnail": "サムネイル画像",
    "cover": "表紙画像",
    "logo": "ロゴ（ヘッダー用）",
    "logo_footer": "ロゴ（フッター用）",
    "favicon": "ファビコン（タブの小さな絵）",
    "og_image": "SNSでシェアされたときの画像",
    "photo_alt": "写真の説明（目の不自由な方向け）",
    "url": "リンク先",
    "button": "ボタンの文字",
    "button_primary": "左のボタンの文字",
    "button_secondary": "右のボタンの文字",
    "line_button": "LINEボタンの文字",
    "map_button": "地図ボタンの文字",
    "submit": "送信ボタンの文字",
    "consent": "同意文",
    "name": "名前",
    "role": "肩書き",
    "key": "項目名",
    "value": "内容",
    "unit": "単位",
    "amount": "数字",
    "time": "時刻",
    "fill": "オレンジの塗りつぶしにする",
    "required": "必須項目にする",
    "reverse": "写真を右側に置く",
    "hide_cta": "下部の共通案内を隠す",
    "per_page": "1ページに表示する件数",
    "blog_home_count": "トップページに出すブログ件数",
    "placeholder": "入力例（うすい文字）",
    "type": "入力の種類",
    "mode": "表示方法",
    "action": "送信先URL",
    "embed_url": "埋め込みURL",
    "coauthored_label": "共著ラベル",
    # 会社情報
    "legal_name": "法人名",
    "office": "事業所名称",
    "industry": "業種",
    "postal": "郵便番号",
    "address": "所在地",
    "tel": "電話番号",
    "fax": "FAX",
    "hours": "営業時間",
    "area": "訪問エリア",
    "base_url": "サイトのURL",
    "instagram": "Instagram",
    "x": "X（旧Twitter）",
    "line": "LINE",
    "line_qr": "LINE友だち追加",
    "map": "Googleマップ",
    "company": "会社情報",
    "job_type": "職種",
    "employment": "雇用形態",
    "salary_summary": "給与（概要）",
    "location": "勤務地",
    "date": "日付",
    "office_name": "事業所",
}

# 配列に「＋追加」ボタンを出すときの、追加ボタンの文言
ADD_LABELS = {
    "posts": "インスタグラムの投稿を追加",
    "members": "スタッフを追加",
    "items": "項目を追加",
    "rows": "行を追加",
    "features": "カードを追加",
    "groups": "グループを追加",
    "blocks": "説明を追加",
    "fields": "入力項目を追加",
    "head_actions": "ボタンを追加",
    "nav": "メニューを追加",
    "footer_nav": "メニューを追加",
    "people": "人物を追加",
    "voices": "声を追加",
}


def label_for(key: str, path: str = "") -> str:
    """項目名から日本語ラベルを返す。"""
    if key in SECTION_LABELS:
        return SECTION_LABELS[key]
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    return key


def is_image(key: str) -> bool:
    return key in IMAGE_KEYS


def is_long(key: str) -> bool:
    return key in LONG_KEYS
