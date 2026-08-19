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
     送信先（Google フォーム）が未設定のときは送信せず、案内だけ表示します。
     設定方法は README.md「フォームの送信先を設定する」を参照してください。 */
  document.querySelectorAll("form[data-form]").forEach(function (form) {
    var status = form.querySelector(".form__status");
    var configured = form.getAttribute("data-configured");

    form.addEventListener("submit", function (e) {
      if (!configured) {
        e.preventDefault();
        if (status) {
          status.textContent =
            "現在このフォームは送信先が未設定です。お手数ですが、お電話またはLINEからご連絡ください。";
          status.style.color = "var(--c-orange)";
        }
        return;
      }
      // Google フォームは応答を読み取れないため、送信後に完了表示へ切り替える
      setTimeout(function () {
        form.reset();
        if (status) {
          status.textContent = "送信しました。ご連絡ありがとうございます。";
          status.style.color = "var(--c-orange)";
        }
      }, 800);
    });
  });
})();
