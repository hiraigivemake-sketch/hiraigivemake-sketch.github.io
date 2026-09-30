/* クリケア訪問看護ステーション — サイト共通スクリプト */
(function () {
  "use strict";

  /* ---------------------------------------------- モバイルメニュー開閉 */
  var menuBtn = document.querySelector(".header__menu-btn");
  if (menuBtn) {
    menuBtn.addEventListener("click", function () {
      var open = document.body.classList.toggle("is-menu-open");
      menuBtn.setAttribute("aria-expanded", String(open));
      menuBtn.setAttribute("aria-label", open ? "メニューを閉じる" : "メニューを開く");
    });
    document.querySelectorAll(".mobile-menu a").forEach(function (a) {
      a.addEventListener("click", function () {
        document.body.classList.remove("is-menu-open");
        menuBtn.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ---------------------------------------------- 現在地のナビを強調 */
  var here = location.pathname.replace(/index\.html$/, "");
  document.querySelectorAll(".header__link, .mobile-menu a").forEach(function (a) {
    var href = a.getAttribute("href");
    if (href && href !== "/" && here.indexOf(href) === 0) {
      a.style.color = "var(--c-orange)";
    }
  });

  /* ---------------------------------------------- フォーム送信
     送信先（ロリポップの受け取りプログラム）が設定されていれば、画面を移動せずに送ります。
     設定されていないあいだは送信せず、電話・LINEをご案内します。 */
  document.querySelectorAll("form[data-form]").forEach(function (form) {
    var status = form.querySelector(".form__status");
    var endpoint = form.getAttribute("data-endpoint");
    var button = form.querySelector("button[type=submit]");

    // 表示した時刻を記録（一瞬で送信されたら自動プログラムとみなすため）
    var t = form.querySelector('input[name="_t"]');
    if (t) t.value = Math.floor(Date.now() / 1000);

    function say(message, ok) {
      if (!status) return;
      status.textContent = message;
      status.classList.toggle("is-ok", !!ok);
      status.classList.toggle("is-ng", !ok);
    }

    form.addEventListener("submit", function (e) {
      if (!endpoint) {
        e.preventDefault();
        say("ただいまフォームの準備中です。お手数ですが、お電話（0745-76-5825）またはLINEからご連絡ください。", false);
        return;
      }

      // 画面を移動させずに送る
      e.preventDefault();
      var data = new FormData(form);
      data.set("_ajax", "1");

      button.disabled = true;
      var original = button.textContent;
      button.textContent = "送信中…";
      say("", true);

      fetch(endpoint, { method: "POST", body: new URLSearchParams(data) })
        .then(function (r) { return r.json().catch(function () { return { ok: r.ok }; }); })
        .then(function (res) {
          if (res.ok) {
            form.reset();
            if (t) t.value = Math.floor(Date.now() / 1000);
            say("送信しました。担当者より折り返しご連絡いたします。", true);
          } else {
            say(res.error || "送信できませんでした。お手数ですが、お電話（0745-76-5825）でご連絡ください。", false);
          }
        })
        .catch(function () {
          // 通信に失敗したときは、ふつうの送信（画面が移動する方式）に切り替える
          var flag = form.querySelector('input[name="_ajax"]');
          if (flag) flag.value = "0";
          form.submit();
        })
        .finally(function () {
          button.disabled = false;
          button.textContent = original;
        });
    });
  });

})();
