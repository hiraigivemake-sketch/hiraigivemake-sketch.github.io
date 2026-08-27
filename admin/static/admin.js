/* クリケア サイト管理画面 — 画面の動き */
(function () {
  "use strict";

  /* ------------------------------------------------------ お知らせ表示 */
  var toastEl = null;
  function toast(message, isError) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "toast";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = message;
    toastEl.classList.toggle("is-error", !!isError);
    toastEl.classList.add("is-show");
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(function () {
      toastEl.classList.remove("is-show");
    }, isError ? 6000 : 2600);
  }
  window.adminToast = toast;

  /* ------------------------------------------------------ 画像選択モーダル */
  var modal = document.getElementById("imgModal");
  var pickGrid = document.getElementById("pickGrid");
  var pickSearch = document.getElementById("pickSearch");
  var pickUpload = document.getElementById("pickUpload");
  var pickIg = document.getElementById("pickIg");
  var pickLib = document.getElementById("pickLib");
  var igSetup = document.getElementById("igSetup");
  var igToken = document.getElementById("igToken");
  var igSave = document.getElementById("igSave");
  var igError = document.getElementById("igError");
  var allImages = [];
  var onPick = null;

  function openPicker(callback) {
    onPick = callback;
    modal.classList.add("is-open");
    pickSearch.value = "";
    showLibrary();
  }

  /* ---------------------------------------- 画像ライブラリ表示 */
  function showLibrary() {
    igSetup.hidden = true;
    pickGrid.hidden = false;
    pickSearch.parentNode.hidden = false;
    pickIg.hidden = false;
    pickLib.hidden = true;
    loadImages().then(function () {
      renderPick(pickSearch.value);
      pickSearch.focus();
    });
  }

  /* ---------------------------------------- インスタグラム表示 */
  function showInstagram() {
    igSetup.hidden = true;
    pickGrid.hidden = false;
    pickSearch.parentNode.hidden = true;
    pickIg.hidden = true;
    pickLib.hidden = false;
    pickGrid.innerHTML = '<p style="color:#6e5a47">インスタグラムから読み込んでいます…</p>';

    fetch("/api/instagram/media")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.configured) { showIgSetup(""); return; }
        if (d.error) { pickGrid.innerHTML = '<p style="color:#b03a24">' + d.error + "</p>"; return; }
        if (!d.items.length) { pickGrid.innerHTML = '<p style="color:#6e5a47">投稿が見つかりませんでした。</p>'; return; }
        renderInstagram(d.items);
      })
      .catch(function () {
        pickGrid.innerHTML = '<p style="color:#b03a24">読み込みに失敗しました。</p>';
      });
  }

  function renderInstagram(items) {
    pickGrid.innerHTML = "";
    items.forEach(function (post) {
      var b = document.createElement("button");
      b.type = "button";
      b.innerHTML =
        '<img src="' + post.thumb + '" alt="" loading="lazy">' +
        "<span>" + (post.date || "") + (post.caption ? "　" + post.caption : "") + "</span>";
      b.addEventListener("click", function () {
        b.disabled = true;
        b.querySelector("span").textContent = "取り込んでいます…";
        fetch("/api/instagram/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: post.id })
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.ok) { alert(d.error || "取り込めませんでした"); b.disabled = false; return; }
            allImages = [];
            if (onPick) onPick(d.path);
            closePicker();
          });
      });
      pickGrid.appendChild(b);
    });
  }

  /* ---------------------------------------- カギの登録 */
  function showIgSetup(message) {
    pickGrid.hidden = true;
    igSetup.hidden = false;
    igError.textContent = message || "";
    igToken.value = "";
    igToken.focus();
  }

  if (igSave) {
    igSave.addEventListener("click", function () {
      var v = igToken.value.trim();
      if (!v) { igError.textContent = "カギを貼り付けてください。"; return; }
      igSave.disabled = true;
      igError.textContent = "確認しています…";
      fetch("/api/instagram/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: v })
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          igSave.disabled = false;
          igToken.value = "";
          if (!d.ok) { igError.textContent = d.error || "登録できませんでした。"; return; }
          showInstagram();
        });
    });
  }

  if (pickIg) pickIg.addEventListener("click", showInstagram);
  if (pickLib) pickLib.addEventListener("click", showLibrary);
  function closePicker() {
    modal.classList.remove("is-open");
    onPick = null;
  }
  window.openImagePicker = openPicker;

  function loadImages() {
    return fetch("/api/images")
      .then(function (r) { return r.json(); })
      .then(function (data) { allImages = data.images || []; });
  }

  function renderPick(keyword) {
    var list = allImages.filter(function (p) {
      return !keyword || p.toLowerCase().indexOf(keyword.toLowerCase()) >= 0;
    });
    pickGrid.innerHTML = "";
    if (!list.length) {
      pickGrid.innerHTML = '<p style="color:#6e5a47">見つかりませんでした。</p>';
      return;
    }
    list.slice(0, 400).forEach(function (path) {
      var b = document.createElement("button");
      b.type = "button";
      b.innerHTML =
        '<img src="/asset' + path + '" alt="" loading="lazy">' +
        "<span>" + path.split("/").pop() + "</span>";
      b.addEventListener("click", function () {
        if (onPick) onPick(path);
        closePicker();
      });
      pickGrid.appendChild(b);
    });
  }

  if (modal) {
    pickSearch.addEventListener("input", function () { renderPick(pickSearch.value); });
    modal.addEventListener("click", function (e) { if (e.target === modal) closePicker(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("is-open")) closePicker();
    });
    document.getElementById("pickClose").addEventListener("click", closePicker);
    pickUpload.addEventListener("change", function () {
      if (!pickUpload.files.length) return;
      uploadFiles(pickUpload.files).then(function (paths) {
        pickUpload.value = "";
        if (paths.length && onPick) {
          onPick(paths[0]);
          closePicker();
          toast("アップロードしました");
        }
      });
    });
  }

  function uploadFiles(files) {
    var form = new FormData();
    for (var i = 0; i < files.length; i++) form.append("file", files[i]);
    return fetch("/api/upload", { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { toast(data.error, true); return []; }
        allImages = (data.paths || []).concat(allImages);
        return data.paths || [];
      })
      .catch(function () { toast("アップロードに失敗しました", true); return []; });
  }
  window.adminUpload = uploadFiles;

  /* ------------------------------------------------------ 画像フィールド */
  function setImageField(wrap, path) {
    var input = wrap.querySelector("input[data-path]");
    var prev = wrap.querySelector(".imgfield__preview");
    var label = wrap.querySelector(".imgfield__path");
    input.value = path;
    if (path) {
      prev.style.backgroundImage = 'url("/asset' + path + '")';
      prev.textContent = "";
    } else {
      prev.style.backgroundImage = "";
      prev.textContent = "画像なし";
    }
    label.textContent = path || "（未設定）";
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-act]");
    if (!btn) return;
    var act = btn.getAttribute("data-act");

    /* 画像を選ぶ */
    if (act === "pick-image") {
      var wrap = btn.closest(".imgfield");
      openPicker(function (path) { setImageField(wrap, path); });
    }

    /* 画像を外す */
    if (act === "clear-image") {
      setImageField(btn.closest(".imgfield"), "");
    }

    /* 画像リスト：追加 */
    if (act === "imglist-add") {
      var list = btn.closest(".field").querySelector(".imglist");
      openPicker(function (path) { addImageToList(list, path); });
    }

    /* 画像リスト：削除 */
    if (act === "imglist-del") {
      var item = btn.closest(".imglist__item");
      var parent = item.parentNode;
      item.remove();
      renumberImageList(parent);
    }

    /* 画像リスト：並べ替え */
    if (act === "imglist-left" || act === "imglist-right") {
      var it = btn.closest(".imglist__item");
      var box = it.parentNode;
      if (act === "imglist-left" && it.previousElementSibling) {
        box.insertBefore(it, it.previousElementSibling);
      } else if (act === "imglist-right" && it.nextElementSibling &&
                 it.nextElementSibling.classList.contains("imglist__item")) {
        box.insertBefore(it.nextElementSibling, it);
      }
      renumberImageList(box);
    }

    /* 繰り返し項目：追加 */
    if (act === "repeat-add") {
      addRepeatItem(btn);
    }

    /* 繰り返し項目：削除 */
    if (act === "repeat-del") {
      var card = btn.closest(".repeat-item");
      var host = card.parentNode;
      if (host.querySelectorAll(".repeat-item").length <= 1) {
        if (!confirm("最後の1件です。本当に削除しますか？")) return;
      }
      card.remove();
      renumberRepeat(host);
    }

    /* 繰り返し項目：並べ替え */
    if (act === "repeat-up" || act === "repeat-down") {
      var c = btn.closest(".repeat-item");
      var h = c.parentNode;
      if (act === "repeat-up" && c.previousElementSibling &&
          c.previousElementSibling.classList.contains("repeat-item")) {
        h.insertBefore(c, c.previousElementSibling);
      } else if (act === "repeat-down" && c.nextElementSibling &&
                 c.nextElementSibling.classList.contains("repeat-item")) {
        h.insertBefore(c.nextElementSibling, c);
      }
      renumberRepeat(h);
    }

    /* 本文に画像を挿入 */
    if (act === "insert-image") {
      var ta = document.querySelector(btn.getAttribute("data-target"));
      openPicker(function (path) {
        var pos = ta.selectionStart || ta.value.length;
        var snippet = "\n\n![](" + path + ")\n\n";
        ta.value = ta.value.slice(0, pos) + snippet + ta.value.slice(pos);
        ta.focus();
        ta.selectionStart = ta.selectionEnd = pos + snippet.length;
      });
    }
  });

  function addImageToList(list, path) {
    var item = document.createElement("div");
    item.className = "imglist__item";
    item.innerHTML =
      '<img src="/asset' + path + '" alt="">' +
      '<input type="hidden" data-path="" value="' + path + '">' +
      '<div class="imglist__tools">' +
      '<button type="button" data-act="imglist-left" title="左へ">←</button>' +
      '<button type="button" data-act="imglist-del" title="外す">✕</button>' +
      '<button type="button" data-act="imglist-right" title="右へ">→</button>' +
      "</div>";
    list.insertBefore(item, list.querySelector(".imglist__add"));
    renumberImageList(list);
  }

  function renumberImageList(list) {
    var base = list.getAttribute("data-base");
    list.querySelectorAll(".imglist__item input").forEach(function (input, i) {
      input.setAttribute("data-path", base + "[" + i + "]");
    });
  }

  function addRepeatItem(btn) {
    var host = document.querySelector(btn.getAttribute("data-host"));
    var items = host.querySelectorAll(":scope > .repeat-item");
    if (!items.length) return;
    var clone = items[items.length - 1].cloneNode(true);

    // 値を空にする（選択肢や真偽値は初期状態へ）
    clone.querySelectorAll("input[type=text], textarea").forEach(function (el) { el.value = ""; });
    clone.querySelectorAll("input[type=checkbox]").forEach(function (el) { el.checked = false; });
    clone.querySelectorAll("input[type=number]").forEach(function (el) { el.value = ""; });
    clone.querySelectorAll("select").forEach(function (el) { el.selectedIndex = 0; });
    clone.querySelectorAll(".imgfield").forEach(function (w) { setImageField(w, ""); });
    clone.querySelectorAll(".imglist__item").forEach(function (n) { n.remove(); });

    host.appendChild(clone);
    renumberRepeat(host);
    clone.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renumberRepeat(host) {
    var base = host.getAttribute("data-base");
    var items = host.querySelectorAll(":scope > .repeat-item");
    items.forEach(function (item, i) {
      var no = item.querySelector(".repeat-item__no");
      if (no) no.textContent = i + 1;
      item.querySelectorAll("[data-path]").forEach(function (el) {
        var p = el.getAttribute("data-path");
        var rest = p.slice(p.indexOf("]") + 1);
        // base[<旧index>]<残り> → base[<新index>]<残り>
        if (p.indexOf(base + "[") === 0) {
          el.setAttribute("data-path", base + "[" + i + "]" + rest);
        }
      });
      item.querySelectorAll(".imglist").forEach(function (list) {
        var b = list.getAttribute("data-base");
        var r = b.slice(b.indexOf("]") + 1);
        list.setAttribute("data-base", base + "[" + i + "]" + r);
        renumberImageList(list);
      });
    });
  }

  /* ------------------------------------------------------ 保存 */
  function buildTree() {
    var root = {};
    document.querySelectorAll("[data-path]").forEach(function (el) {
      var path = el.getAttribute("data-path");
      if (!path) return;
      var value;
      if (el.type === "checkbox") value = el.checked;
      else if (el.type === "number") value = el.value === "" ? "" : Number(el.value);
      else if (el.dataset.lines === "1") {
        value = el.value.split("\n").map(function (s) { return s.trim(); })
                        .filter(function (s) { return s.length; });
      } else value = el.value;

      var tokens = path.match(/[^.\[\]]+|\[\d+\]/g) || [];
      var cur = root;
      for (var i = 0; i < tokens.length; i++) {
        var t = tokens[i];
        var isIndex = t.charAt(0) === "[";
        var key = isIndex ? parseInt(t.slice(1, -1), 10) : t;
        var last = i === tokens.length - 1;
        if (last) {
          cur[key] = value;
        } else {
          var nextIsIndex = tokens[i + 1].charAt(0) === "[";
          if (cur[key] === undefined) cur[key] = nextIsIndex ? [] : {};
          cur = cur[key];
        }
      }
    });
    return compact(root);
  }

  // 削除でできた配列の穴を詰める
  function compact(node) {
    if (Array.isArray(node)) return node.filter(function (v) { return v !== undefined; }).map(compact);
    if (node && typeof node === "object") {
      Object.keys(node).forEach(function (k) { node[k] = compact(node[k]); });
      return node;
    }
    return node;
  }

  var saveBtn = document.getElementById("saveBtn");
  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      saveBtn.disabled = true;
      saveBtn.textContent = "保存中…";
      fetch(saveBtn.getAttribute("data-url"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildTree()),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            toast(data.message || "保存しました");
            window.onbeforeunload = null;
            if (data.redirect) setTimeout(function () { location.href = data.redirect; }, 700);
          } else {
            toast(data.error || "保存できませんでした", true);
          }
        })
        .catch(function () { toast("保存できませんでした", true); })
        .finally(function () {
          saveBtn.disabled = false;
          saveBtn.textContent = "保存する";
        });
    });
  }

  /* 未保存のまま離れようとしたら確認する */
  var dirty = false;
  document.addEventListener("input", function (e) {
    if (e.target.closest("form, .content__inner") && !dirty && saveBtn) {
      dirty = true;
      window.onbeforeunload = function () { return "保存していない変更があります。"; };
    }
  });

  /* ------------------------------------------------------ 画像ライブラリ */
  var drop = document.getElementById("dropzone");
  if (drop) {
    var input = document.getElementById("dropInput");
    ["dragenter", "dragover"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("is-over"); });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("is-over"); });
    });
    drop.addEventListener("drop", function (e) {
      if (e.dataTransfer.files.length) doUpload(e.dataTransfer.files);
    });
    drop.addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () {
      if (input.files.length) doUpload(input.files);
    });
    function doUpload(files) {
      toast("アップロード中…");
      uploadFiles(files).then(function (paths) {
        if (paths.length) { toast(paths.length + "件アップロードしました"); location.reload(); }
      });
    }
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (b) {
      navigator.clipboard.writeText(b.getAttribute("data-copy"));
      toast("パスをコピーしました");
    }
    var d = e.target.closest("[data-delete-image]");
    if (d) {
      var p = d.getAttribute("data-delete-image");
      if (!confirm(p + "\nこの画像をゴミ箱へ移動します。よろしいですか？")) return;
      fetch("/api/delete-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: p }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) { toast("移動しました"); location.reload(); }
          else toast(data.error || "削除できませんでした", true);
        });
    }
  });

  /* ------------------------------------------------------ 読み込み完了の目印
     （動作確認用。これが付いていればスクリプトは正常に読み込まれています） */
  document.documentElement.setAttribute("data-admin-js", "ready");

  /* ------------------------------------------------------ 一覧の絞り込み */
  var filter = document.getElementById("listFilter");
  if (filter) {
    filter.addEventListener("input", function () {
      var q = filter.value.toLowerCase();
      document.querySelectorAll("[data-search]").forEach(function (row) {
        var hit = row.getAttribute("data-search").toLowerCase().indexOf(q) >= 0;
        row.style.display = hit ? "" : "none";
      });
    });
  }
})();
