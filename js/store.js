/**
 * store.js — Vender Resale shared storefront module
 * Exposes window.VR as an IIFE. No ES modules, no frameworks.
 */
(function (global) {
  'use strict';

  // ─── Internal state ────────────────────────────────────────────────────────

  var CATALOG_KEY   = 'vr_catalog';
  var CART_KEY      = 'vr_cart';
  var _catalogCache = null;          // in-memory cache
  var _cartListeners = [];

  // ─── Catalog ───────────────────────────────────────────────────────────────

  function _loadCatalog() {
    if (_catalogCache) {
      return Promise.resolve(_catalogCache);
    }

    var stored = null;
    try {
      var raw = sessionStorage.getItem(CATALOG_KEY);
      if (raw) stored = JSON.parse(raw);
    } catch (e) {}

    if (stored) {
      _catalogCache = stored;
      global._VR_CATALOG = stored;
      return Promise.resolve(stored);
    }

    return fetch('/data/catalog.json')
      .then(function (res) {
        if (!res.ok) throw new Error('catalog fetch failed: ' + res.status);
        return res.json();
      })
      .then(function (data) {
        var catalog = Array.isArray(data) ? data : (data.products || []);
        _catalogCache = catalog;
        global._VR_CATALOG = catalog;
        try { sessionStorage.setItem(CATALOG_KEY, JSON.stringify(catalog)); } catch (e) {}
        return catalog;
      });
  }

  function getCatalog() {
    return _loadCatalog();
  }

  function getProduct(id) {
    return _loadCatalog().then(function (catalog) {
      var idNum = parseInt(id, 10);
      for (var i = 0; i < catalog.length; i++) {
        if (catalog[i].id === idNum) return catalog[i];
      }
      return null;
    });
  }

  function searchProducts(catalog, query) {
    if (!query) return catalog.slice();
    var q = query.toLowerCase();
    return catalog.filter(function (p) {
      return (
        (p.name        && p.name.toLowerCase().indexOf(q)        !== -1) ||
        (p.description && p.description.toLowerCase().indexOf(q) !== -1)
      );
    });
  }

  function filterByCategory(catalog, cat) {
    if (!cat) return catalog.slice();
    var c = cat.toLowerCase();
    return catalog.filter(function (p) {
      return p.category && p.category.toLowerCase() === c;
    });
  }

  // ─── Cart internals ────────────────────────────────────────────────────────

  function _readCart() {
    try {
      var raw = localStorage.getItem(CART_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return [];
  }

  function _writeCart(items) {
    try { localStorage.setItem(CART_KEY, JSON.stringify(items)); } catch (e) {}
    _notifyCartChange(items);
  }

  function _itemKey(id, variant) {
    return String(id) + '::' + (variant || '');
  }

  function _notifyCartChange(items) {
    var count = cart.count();
    // Update all badge elements
    var badges = document.querySelectorAll('.cart-count');
    for (var i = 0; i < badges.length; i++) {
      badges[i].textContent = count;
    }
    // Call subscribers
    for (var j = 0; j < _cartListeners.length; j++) {
      try { _cartListeners[j](items); } catch (e) {}
    }
  }

  // ─── Cart public API ───────────────────────────────────────────────────────

  var cart = {
    add: function (product, quantity, variant) {
      quantity = (quantity === undefined || quantity === null) ? 1 : parseInt(quantity, 10);
      variant  = variant || null;
      if (quantity < 1) return;

      var items = _readCart();
      var key   = _itemKey(product.id, variant);
      var found = false;

      for (var i = 0; i < items.length; i++) {
        if (_itemKey(items[i].id, items[i].variant) === key) {
          items[i].quantity += quantity;
          found = true;
          break;
        }
      }

      if (!found) {
        items.push({
          id:        product.id,
          name:      product.name,
          price:     product.price,
          image_url: product.image_url || (product.images && product.images[0]) || '',
          quantity:  quantity,
          variant:   variant
        });
      }

      _writeCart(items);
    },

    remove: function (id, variant) {
      variant = variant || null;
      var key   = _itemKey(id, variant);
      var items = _readCart().filter(function (item) {
        return _itemKey(item.id, item.variant) !== key;
      });
      _writeCart(items);
    },

    update: function (id, variant, quantity) {
      variant  = variant || null;
      quantity = parseInt(quantity, 10);
      if (quantity <= 0) {
        cart.remove(id, variant);
        return;
      }
      var key   = _itemKey(id, variant);
      var items = _readCart();
      for (var i = 0; i < items.length; i++) {
        if (_itemKey(items[i].id, items[i].variant) === key) {
          items[i].quantity = quantity;
          break;
        }
      }
      _writeCart(items);
    },

    clear: function () {
      _writeCart([]);
    },

    get: function () {
      return _readCart();
    },

    count: function () {
      var items = _readCart();
      var n = 0;
      for (var i = 0; i < items.length; i++) n += (items[i].quantity || 1);
      return n;
    },

    total: function () {
      var items = _readCart();
      var t = 0;
      for (var i = 0; i < items.length; i++) {
        t += (parseFloat(items[i].price) || 0) * (items[i].quantity || 1);
      }
      return Math.round(t * 100) / 100;
    },

    onChange: function (fn) {
      if (typeof fn === 'function') _cartListeners.push(fn);
    }
  };

  // ─── Helpers ───────────────────────────────────────────────────────────────

  function formatPrice(n) {
    return '$' + parseFloat(n).toFixed(2);
  }

  function getParam(key) {
    try {
      return new URLSearchParams(global.location.search).get(key);
    } catch (e) {
      return null;
    }
  }

  function setParams(obj) {
    try {
      var params = new URLSearchParams(global.location.search);
      var keys = Object.keys(obj);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        if (obj[k] === null || obj[k] === undefined || obj[k] === '') {
          params.delete(k);
        } else {
          params.set(k, obj[k]);
        }
      }
      var newUrl = global.location.pathname + (params.toString() ? '?' + params.toString() : '');
      global.history.replaceState(null, '', newUrl);
    } catch (e) {}
  }

  function showToast(message) {
    var existing = document.getElementById('vr-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = 'vr-toast';
    toast.textContent = message;
    toast.style.cssText = [
      'position:fixed',
      'bottom:24px',
      'right:24px',
      'background:#1a1a1a',
      'color:#f0c040',
      'padding:12px 20px',
      'border-radius:6px',
      'font-size:14px',
      'font-family:inherit',
      'box-shadow:0 4px 16px rgba(0,0,0,0.4)',
      'z-index:9999',
      'opacity:0',
      'transition:opacity 0.2s ease',
      'max-width:320px',
      'word-break:break-word'
    ].join(';');

    document.body.appendChild(toast);
    // Trigger reflow before transitioning
    void toast.offsetWidth;
    toast.style.opacity = '1';

    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { if (toast.parentNode) toast.remove(); }, 220);
    }, 2500);
  }

  function renderSkeleton(container, count) {
    if (!container) return;
    var html = '';
    for (var i = 0; i < count; i++) {
      html += [
        '<div class="vr-skeleton-card" style="',
          'border-radius:8px;overflow:hidden;background:#1e1e1e;',
          'animation:vr-shimmer 1.4s infinite linear;">',
          '<div style="width:100%;padding-top:100%;background:linear-gradient(',
            '90deg,#2a2a2a 25%,#333 50%,#2a2a2a 75%)',
            ';background-size:200% 100%;animation:vr-shimmer 1.4s infinite linear;"></div>',
          '<div style="padding:12px">',
            '<div style="height:14px;background:#2a2a2a;border-radius:4px;margin-bottom:8px;',
              'background:linear-gradient(90deg,#2a2a2a 25%,#333 50%,#2a2a2a 75%)',
              ';background-size:200% 100%;animation:vr-shimmer 1.4s infinite linear;"></div>',
            '<div style="height:14px;width:60%;background:#2a2a2a;border-radius:4px;',
              'background:linear-gradient(90deg,#2a2a2a 25%,#333 50%,#2a2a2a 75%)',
              ';background-size:200% 100%;animation:vr-shimmer 1.4s infinite linear;"></div>',
          '</div>',
        '</div>'
      ].join('');
    }

    // Inject keyframes once
    if (!document.getElementById('vr-skeleton-style')) {
      var style = document.createElement('style');
      style.id = 'vr-skeleton-style';
      style.textContent = [
        '@keyframes vr-shimmer{',
          '0%{background-position:200% 0}',
          '100%{background-position:-200% 0}',
        '}'
      ].join('');
      document.head.appendChild(style);
    }

    container.innerHTML = html;
  }

  // ─── Product card ──────────────────────────────────────────────────────────

  function productCardHTML(product) {
    var imgSrc   = product.image_url || (product.images && product.images[0]) || '';
    var name     = (product.name || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    var category = (product.category || '').replace(/</g, '&lt;');
    var price    = formatPrice(product.price || 0);
    var id       = product.id;

    return [
      '<div class="vr-product-card" style="',
        'position:relative;border-radius:8px;overflow:hidden;',
        'background:#1a1a1a;display:flex;flex-direction:column;',
        'box-shadow:0 2px 8px rgba(0,0,0,0.3);transition:transform 0.15s ease;">',

        // Image wrapper — 1:1 aspect ratio
        '<div style="position:relative;width:100%;padding-top:100%;overflow:hidden;">',
          '<img src="', imgSrc, '" alt="', name, '"',
            ' style="position:absolute;top:0;left:0;width:100%;height:100%;',
            'object-fit:cover;" loading="lazy" onerror="this.style.background=\'#2a2a2a\'">',

          // Category badge overlay
          category
            ? '<span style="position:absolute;top:8px;left:8px;background:rgba(0,0,0,0.72);' +
              'color:#f0c040;font-size:10px;font-weight:600;letter-spacing:0.05em;' +
              'padding:3px 8px;border-radius:4px;text-transform:uppercase;">' +
              category + '</span>'
            : '',
        '</div>',

        // Card body
        '<div style="padding:12px 14px 14px;display:flex;flex-direction:column;flex:1;">',

          // Product name — 2 lines max
          '<p style="margin:0 0 8px;font-size:14px;font-weight:500;color:#e8e8e8;',
            'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;',
            'overflow:hidden;line-height:1.4;min-height:2.8em;">',
            name,
          '</p>',

          // Price
          '<p style="margin:0 0 12px;font-size:16px;font-weight:700;color:#f0c040;">',
            price,
          '</p>',

          // Actions
          '<div style="display:flex;gap:8px;margin-top:auto;">',
            '<button data-id="', id, '"',
              ' class="vr-add-to-cart"',
              ' style="flex:1;padding:8px 10px;background:#f0c040;color:#111;',
              'border:none;border-radius:5px;font-size:13px;font-weight:600;',
              'cursor:pointer;transition:background 0.15s;">',
              'Add to Cart',
            '</button>',
            '<a href="product.html?id=', id, '"',
              ' style="display:flex;align-items:center;padding:8px 12px;',
              'background:#2a2a2a;color:#e8e8e8;border-radius:5px;font-size:13px;',
              'text-decoration:none;white-space:nowrap;transition:background 0.15s;">',
              'View',
            '</a>',
          '</div>',

        '</div>',
      '</div>'
    ].join('');
  }

  // ─── Wire up Add-to-Cart via event delegation ──────────────────────────────

  function _bindCartButtons() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.vr-add-to-cart') : null;
      if (!btn) return;
      var id = parseInt(btn.getAttribute('data-id'), 10);
      if (isNaN(id)) return;

      getProduct(id).then(function (product) {
        if (!product) return;
        cart.add(product, 1, null);
        showToast(product.name + ' added to cart');
      });
    });
  }

  // ─── Init ──────────────────────────────────────────────────────────────────

  function _init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        cart.onChange(function () {}); // trigger badge update
        _bindCartButtons();
        _notifyCartChange(_readCart()); // set initial badge counts
      });
    } else {
      cart.onChange(function () {});
      _bindCartButtons();
      _notifyCartChange(_readCart());
    }
  }

  // ─── Public API ────────────────────────────────────────────────────────────

  var VR = {
    getCatalog:       getCatalog,
    getProduct:       getProduct,
    searchProducts:   searchProducts,
    filterByCategory: filterByCategory,
    cart:             cart,
    formatPrice:      formatPrice,
    getParam:         getParam,
    setParams:        setParams,
    showToast:        showToast,
    renderSkeleton:   renderSkeleton,
    productCardHTML:  productCardHTML
  };

  global.VR = VR;
  _init();

}(window));
