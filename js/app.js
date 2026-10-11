const accountStorageKey = 'rb-account';
const readStoredJson = (storage, key, fallback = null) => {
  try {
    return JSON.parse(storage.getItem(key) || 'null') ?? fallback;
  } catch {
    storage.removeItem(key);
    return fallback;
  }
};
const currentAccount = readStoredJson(localStorage, accountStorageKey);
const apiBaseUrl = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000/api' : '/api';
const backendRequest = (path, options = {}) => fetch(`${apiBaseUrl}${path}`, {
  ...options,
  headers: {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(currentAccount?.token ? { Authorization: `Bearer ${currentAccount.token}` } : {}),
    ...options.headers
  }
});

if (currentAccount) {
  const accountStyles = document.createElement('style');
  accountStyles.textContent = `
    .account-indicator { display: inline-flex; align-items: center; gap: .45rem; color: #1d1d1d; font-size: .78rem; font-weight: 700; }
    .account-indicator__mark { position: relative; display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; color: #090909; background: #d4af5f; font-size: .7rem; }
    .account-indicator__mark::after { content: ''; position: absolute; right: -1px; bottom: -1px; width: 9px; height: 9px; border: 2px solid #fff; border-radius: 50%; background: #2f9e44; }
    .account-indicator__name { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    @media (max-width: 700px) { .account-indicator__name { display: none; } }
  `;
  document.head.appendChild(accountStyles);

  const accountIndicator = document.createElement('div');
  const initials = currentAccount.name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  accountIndicator.className = 'account-indicator';
  accountIndicator.setAttribute('aria-label', `Signed in as ${currentAccount.name}`);
  const accountMark = document.createElement('span');
  accountMark.className = 'account-indicator__mark';
  accountMark.textContent = initials;
  const accountName = document.createElement('span');
  accountName.className = 'account-indicator__name';
  accountName.textContent = currentAccount.name;
  accountIndicator.append(accountMark, accountName);
  document.querySelector('.header__actions')?.prepend(accountIndicator);

  if (currentAccount.role === 'admin') {
    const adminLink = document.createElement('a');
    adminLink.className = 'admin-dashboard-link';
    adminLink.href = 'admin.html';
    adminLink.textContent = 'Admin dashboard';
    adminLink.title = 'Open admin dashboard';
    document.querySelector('.header__actions')?.prepend(adminLink);
  }
}

const headerInner = document.querySelector('.header__inner');
const mainNavigation = headerInner?.querySelector('.nav');
const headerActions = headerInner?.querySelector('.header__actions');

if (headerInner && mainNavigation && headerActions) {
  const navigationStyles = document.createElement('style');
  navigationStyles.textContent = `
    .site-menu-toggle, .site-nav-overlay { display: none; }
    @media (max-width: 820px) {
      .header { position: sticky; top: 0; z-index: 30; }
      .header__inner { min-height: 64px; gap: 8px; }
      .header__actions { order: 2; gap: 6px; margin-left: auto; }
      .site-menu-toggle {
        order: 3; display: grid; place-content: center; flex: 0 0 44px;
        width: 44px; height: 44px; padding: 0; border: 1px solid rgba(0,0,0,.16);
        border-radius: 4px; color: inherit; background: transparent; cursor: pointer;
      }
      .site-menu-toggle span { display: block; width: 20px; height: 2px; margin: 2px 0; background: currentColor; }
      .nav:not(.site-nav-open) { display: none !important; }
      .nav.site-nav-open {
        position: fixed; inset: 0 0 0 auto; z-index: 1002; display: flex !important;
        width: min(360px, 88vw); height: 100vh; height: 100dvh; flex-direction: column;
        align-items: stretch; justify-content: flex-start; gap: 0; margin: 0; padding: 72px 18px 24px;
        overflow-y: auto; overscroll-behavior: contain; background: var(--white, #fff);
        box-shadow: -12px 0 32px rgba(0,0,0,.16); transform: none; visibility: visible;
      }
      .nav.site-nav-open a {
        display: flex; min-height: 50px; align-items: center; padding: 9px 10px;
        border-bottom: 1px solid var(--line, rgba(0,0,0,.1)); font-size: 15px; text-decoration: none;
      }
      .nav.site-nav-open a::after { display: none; }
      .nav.site-nav-open a.active { color: #866325; background: rgba(197,155,82,.1); }
      .site-nav-overlay {
        position: fixed; inset: 0; z-index: 1001; display: block; width: 100%; height: 100%;
        padding: 0; border: 0; background: rgba(9,9,9,.48); opacity: 0; visibility: hidden;
        pointer-events: none; transition: opacity .18s ease, visibility .18s ease;
      }
      .site-nav-overlay.is-open { opacity: 1; visibility: visible; pointer-events: auto; }
      body.site-nav-open { overflow: hidden; }
    }
  `;
  document.head.appendChild(navigationStyles);

  if (!mainNavigation.id) mainNavigation.id = 'site-primary-navigation';
  const menuToggle = document.createElement('button');
  menuToggle.className = 'site-menu-toggle';
  menuToggle.type = 'button';
  menuToggle.setAttribute('aria-label', 'Open navigation menu');
  menuToggle.setAttribute('aria-controls', mainNavigation.id);
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.innerHTML = '<span></span><span></span><span></span>';
  headerInner.insertBefore(menuToggle, headerActions);

  const navigationOverlay = document.createElement('button');
  navigationOverlay.className = 'site-nav-overlay';
  navigationOverlay.type = 'button';
  navigationOverlay.setAttribute('aria-label', 'Close navigation menu');
  navigationOverlay.setAttribute('aria-hidden', 'true');
  document.querySelector('.header')?.appendChild(navigationOverlay);

  const closeNavigation = (restoreFocus = true) => {
    mainNavigation.classList.remove('site-nav-open');
    navigationOverlay.classList.remove('is-open');
    navigationOverlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('site-nav-open');
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.setAttribute('aria-label', 'Open navigation menu');
    if (restoreFocus) menuToggle.focus();
  };

  menuToggle.addEventListener('click', () => {
    const isOpen = menuToggle.getAttribute('aria-expanded') !== 'true';
    if (!isOpen) return closeNavigation();
    mainNavigation.classList.add('site-nav-open');
    navigationOverlay.classList.add('is-open');
    navigationOverlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('site-nav-open');
    menuToggle.setAttribute('aria-expanded', 'true');
    menuToggle.setAttribute('aria-label', 'Close navigation menu');
    mainNavigation.querySelector('a')?.focus();
  });
  navigationOverlay.addEventListener('click', () => closeNavigation());
  mainNavigation.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeNavigation(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
      closeNavigation();
    }
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 820 && menuToggle.getAttribute('aria-expanded') === 'true') {
      closeNavigation(false);
    }
  });
}

const visitorStorageKey = 'rb-visitor-id';
const visitorId = sessionStorage.getItem(visitorStorageKey) || crypto.randomUUID();
sessionStorage.setItem(visitorStorageKey, visitorId);
backendRequest('/visits', {
  method: 'POST',
  body: JSON.stringify({ visitorId, page: window.location.pathname })
}).catch(() => { });

const announcementBar = document.querySelector('.announcement-bar');
const closeAnnouncement = document.querySelector('.announcement-bar__close');

if (announcementBar && closeAnnouncement) {
  closeAnnouncement.addEventListener('click', () => {
    announcementBar.style.display = 'none';
  });
}

let catalogProducts = typeof PRODUCT_CATALOG === 'undefined' ? [] : PRODUCT_CATALOG;
const DISCOUNT_RATE = 0.10;
const getDiscountPrice = (product) => product.discountPrice || Math.round(product.price * (1 - DISCOUNT_RATE) / 10) * 10;
const formatMoney = (amount) => `GH₵ ${amount}`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[character]));
const validImageUrl = (value) => {
  try {
    const url = new URL(value, window.location.href);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
};

const catalogPagesFor = (product) => {
  const existing = PRODUCT_CATALOG.find((item) => item.id === product.id);
  if (existing) return existing.pages;
  const category = product.category.toLowerCase();
  const pages = ['new', 'all'];
  if (category.includes('formal')) pages.push('formal', 'men', 'women');
  else if (category.includes('sneaker') || category.includes('boot') || category.includes('shoe')) pages.push('shoes', 'men', 'women');
  else if (category.includes('denim') || category.includes('streetwear') || category.includes('layer')) pages.push('men', 'women');
  else pages.push('men', 'women');
  return pages;
};

const mapApiProduct = (product) => {
  const fallback = PRODUCT_CATALOG.find((item) => item.id === product.id);
  const imageUrl = product.image_url || '';
  const image = window.location.protocol === 'file:' && imageUrl.startsWith('/')
    ? `http://127.0.0.1:8000${imageUrl}`
    : validImageUrl(imageUrl);
  const categoryImage = PRODUCT_CATALOG.find((item) =>
    item.category.toLowerCase() === String(product.category).toLowerCase()
  )?.images[0];
  return {
    id: product.id,
    name: product.name,
    category: product.category,
    description: product.description || '',
    price: Number(product.price),
    stock: Number(product.stock),
    discountPrice: product.discountPrice,
    pages: catalogPagesFor(product),
    images: image
      ? [image, ...(fallback?.images.slice(1) || [])]
      : fallback?.images || [categoryImage || PRODUCT_CATALOG[0].images[0]]
  };
};

const renderCatalogCard = (product, cardStyle) => {
  const discountPrice = getDiscountPrice(product);
  const price = `<span class="product-price__original">${formatMoney(product.price)}</span><span class="product-price__sale">${formatMoney(discountPrice)}</span>`;
  const name = escapeHtml(product.name);
  const category = escapeHtml(product.category);
  const images = encodeURIComponent(JSON.stringify(product.images));
  const image = product.images[0] || '';
  const stock = Number.isFinite(product.stock) ? product.stock : 1;
  const addButton = stock > 0
    ? '<button type="button" class="product-card__quick-add add-to-cart">Add to bag</button>'
    : '<button type="button" class="product-card__quick-add add-to-cart" disabled>Out of stock</button>';
  if (cardStyle === 'home') {
    return `
      <article class="product-card" id="product-${escapeHtml(product.id)}" data-product-id="${escapeHtml(product.id)}" data-original-price="${product.price}" data-sale-price="${discountPrice}" data-description="${escapeHtml(product.description)}">
        <div class="product-card__image-wrapper" data-gallery-images="${images}"><img src="${image}" alt="${name}" /></div>
        <div class="product-card__info">
          <span class="product-card__category">${category}</span>
          <h3 class="product-card__name">${name}</h3>
          <p class="product-card__price">${price}</p>
          ${addButton}
        </div>
      </article>
    `;
  }

  return `
    <article class="product" id="product-${escapeHtml(product.id)}" data-product-id="${escapeHtml(product.id)}" data-original-price="${product.price}" data-sale-price="${discountPrice}" data-description="${escapeHtml(product.description)}">
      <div class="product__image" role="img" aria-label="${name}" data-gallery-images="${images}"${image ? ` style="background-image:url('${escapeHtml(image)}')"` : ''}></div>
      <div class="product__body">
        <span class="product__tag">${category}</span>
        <h3 class="product__name">${name}</h3>
        <p class="product__price">${price}</p>
        <button type="button" class="product__button" ${stock < 1 ? 'disabled' : ''}>${stock > 0 ? 'Add to bag' : 'Out of stock'}</button>
      </div>
    </article>
  `;
};

const renderCatalogGrids = () => {
  document.querySelectorAll('[data-catalog]').forEach((grid) => {
    const page = grid.dataset.catalog;
    const cardStyle = grid.dataset.cardStyle || 'category';
    const visibleProducts = catalogProducts.filter((product) => product.pages.includes(page));
    grid.innerHTML = visibleProducts.length
      ? visibleProducts.map((product) => renderCatalogCard(product, cardStyle)).join('')
      : '<p class="catalog-status">No products are available in this collection yet.</p>';
  });
  products = [...document.querySelectorAll('.product, .product-card')];
  document.querySelectorAll('.catalog-connectivity-status').forEach((status) => status.remove());
};

let products = [];
renderCatalogGrids();

const searchButton = document.querySelector('.header__action-btn');

if (searchButton) {
  const searchPanel = document.createElement('div');
  searchPanel.className = 'search-panel';
  searchPanel.innerHTML = `
    <div class="search-panel__content" role="dialog" aria-label="Search products">
      <label class="search-panel__label" for="site-search">Search products</label>
      <div class="search-panel__row">
        <input id="site-search" class="search-panel__input" type="search" placeholder="Try shirts, dresses or shoes" autocomplete="off">
        <button type="button" class="search-panel__close" aria-label="Close search">&times;</button>
      </div>
      <p class="search-panel__status" aria-live="polite"></p>
      <div class="search-panel__results"></div>
    </div>
  `;
  document.body.appendChild(searchPanel);

  const searchStyles = document.createElement('style');
  searchStyles.textContent = `
    .search-panel { display: none; position: fixed; inset: 0; z-index: 100; padding: max(90px, 12vh) 1rem 1rem; overflow-y: auto; background: rgba(9, 9, 9, 0.48); }
    .search-panel.is-open { display: block; }
    .search-panel__content { width: min(620px, 100%); max-height: min(75vh, 700px); margin: 0 auto; padding: 1.25rem; overflow-y: auto; background: #fff; border-radius: 12px; box-shadow: 0 18px 50px rgba(0, 0, 0, 0.2); }
    .search-panel__label { display: block; margin-bottom: 0.6rem; font-weight: 700; }
    .search-panel__row { display: flex; align-items: center; gap: 0.6rem; }
    .search-panel__input { flex: 1; min-width: 0; padding: 0.8rem 0.9rem; border: 1px solid rgba(0, 0, 0, 0.2); border-radius: 8px; font: inherit; }
    .search-panel__close { border: 0; background: transparent; font-size: 1.7rem; line-height: 1; cursor: pointer; }
    .search-panel__status { min-height: 1.2em; margin: 0.7rem 0 0; color: #666; font-size: 0.9rem; }
    .search-panel__results { display: grid; gap: .5rem; margin-top: .6rem; }
    .search-result { display: grid; grid-template-columns: 56px minmax(0, 1fr) auto; align-items: center; gap: .8rem; padding: .55rem; border: 1px solid rgba(0,0,0,.08); border-radius: 8px; }
    .search-result:hover, .search-result:focus-visible { border-color: #d4af5f; background: #fffaf0; }
    .search-result__image { width: 56px; height: 64px; border-radius: 4px; object-fit: cover; background: #eee; }
    .search-result__name { display: block; font-weight: 700; }
    .search-result__category { display: block; color: #666; font-size: .8rem; }
    .search-result__price { color: #8c2020; font-size: .88rem; font-weight: 700; white-space: nowrap; }
    @media (max-width: 480px) { .search-panel { padding: 1rem .6rem; } .search-panel__content { max-height: 85vh; padding: 1rem; } .search-result { grid-template-columns: 44px minmax(0,1fr); gap: .6rem; } .search-result__image { width: 44px; height: 52px; } .search-result__price { grid-column: 2; } }
    .bag-panel { display: none; position: fixed; inset: 0; z-index: 101; background: rgba(9, 9, 9, 0.48); }
    .bag-panel.is-open { display: block; }
    .bag-panel__content { width: min(420px, calc(100% - 2rem)); height: 100%; margin-left: auto; padding: 1.5rem; overflow-y: auto; background: #fff; box-shadow: -12px 0 35px rgba(0, 0, 0, 0.16); }
    .bag-panel__header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
    .bag-panel__title { margin: 0; font-size: 1.5rem; }
    .bag-panel__close { border: 0; background: transparent; font-size: 1.7rem; line-height: 1; cursor: pointer; }
    .bag-panel__item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 0; border-bottom: 1px solid rgba(0, 0, 0, 0.1); }
    .bag-panel__item-name { margin: 0 0 0.25rem; font-weight: 700; }
    .bag-panel__item-price { margin: 0; color: #666; }
    .bag-panel__remove { border: 0; background: transparent; color: #777; cursor: pointer; text-decoration: underline; }
    .bag-panel__empty { color: #666; }
    .catalog-connectivity-status { grid-column: 1 / -1; padding: .8rem 1rem; border-left: 3px solid #b3261e; color: #65302d; background: #fff4f2; font-size: .85rem; }
    .bag-panel__total { display: flex; justify-content: space-between; margin-top: 1.25rem; font-weight: 700; }
    .bag-panel__payment { margin-top: 1rem; padding: .85rem; border-left: 3px solid #d4af5f; color: #555; background: #fffaf0; font-size: .85rem; line-height: 1.45; }
    .bag-panel__checkout { display: grid; gap: .7rem; margin-top: 1rem; }
    .bag-panel__checkout[hidden] { display: none; }
    .bag-panel__checkout label { display: grid; gap: .35rem; font-size: .76rem; font-weight: 700; }
    .bag-panel__checkout input, .bag-panel__checkout textarea { width: 100%; min-width: 0; padding: .7rem; border: 1px solid rgba(0,0,0,.18); border-radius: 6px; font: inherit; }
    .bag-panel__checkout textarea { min-height: 72px; resize: vertical; }
    .bag-panel__checkout button { padding: .8rem; border: 0; border-radius: 6px; color: #fff; background: #090909; font: inherit; font-weight: 700; cursor: pointer; }
    .bag-panel__status { color: #555; font-size: .85rem; line-height: 1.45; white-space: pre-line; }
  `;
  document.head.appendChild(searchStyles);

  const searchInput = searchPanel.querySelector('.search-panel__input');
  const closeSearch = searchPanel.querySelector('.search-panel__close');
  const searchStatus = searchPanel.querySelector('.search-panel__status');
  const searchResults = searchPanel.querySelector('.search-panel__results');

  const closePanel = () => {
    searchPanel.classList.remove('is-open');
    searchInput.value = '';
    searchStatus.textContent = '';
    searchResults.replaceChildren();
  };

  const filterProducts = () => {
    const query = searchInput.value.trim().toLowerCase();
    searchResults.replaceChildren();
    if (!query) {
      searchStatus.textContent = 'Search all products by name or category.';
      return;
    }

    const matches = catalogProducts.filter((product) => {
      const searchableText = `${product.name} ${product.category} ${product.description} ${product.pages.includes('shoes') ? 'shoe shoes' : ''}`;
      return searchableText.toLowerCase().includes(query);
    });
    searchStatus.textContent = matches.length
      ? `${matches.length} product${matches.length === 1 ? '' : 's'} found`
      : 'No products found. Try another name or category.';
    matches.slice(0, 20).forEach((product) => {
      const result = document.createElement('a');
      result.className = 'search-result';
      const destination = product.pages.includes('all')
        ? 'shop.html'
        : product.pages.includes('formal')
          ? 'shop.html#formal-wear'
          : product.pages.includes('shoes')
            ? 'shoes.html'
            : product.pages.includes('men')
              ? 'men.html'
              : product.pages.includes('women')
                ? 'women.html'
                : 'index.html';
      result.href = `${destination}#product-${encodeURIComponent(product.id)}`;

      const image = document.createElement('img');
      image.className = 'search-result__image';
      image.src = product.images[0] || '';
      image.alt = '';
      image.loading = 'lazy';
      const details = document.createElement('span');
      const name = document.createElement('span');
      name.className = 'search-result__name';
      name.textContent = product.name;
      const category = document.createElement('span');
      category.className = 'search-result__category';
      category.textContent = product.category;
      details.append(name, category);
      const price = document.createElement('span');
      price.className = 'search-result__price';
      price.textContent = formatMoney(getDiscountPrice(product));
      result.append(image, details, price);
      searchResults.append(result);
    });
  };

  searchButton.addEventListener('click', () => {
    searchPanel.classList.add('is-open');
    filterProducts();
    searchInput.focus();
  });
  searchInput.addEventListener('input', filterProducts);
  closeSearch.addEventListener('click', closePanel);
  searchPanel.addEventListener('click', (event) => {
    if (event.target === searchPanel) closePanel();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closePanel();
  });
}

const assistantStyles = document.createElement('style');
assistantStyles.textContent = `
  .genius-launcher { position: fixed; right: 1.2rem; bottom: 1.2rem; z-index: 120; width: 54px; height: 54px; border: 0; border-radius: 50%; color: #090909; background: #d4af5f; box-shadow: 0 8px 24px rgba(0,0,0,.2); font-weight: 800; cursor: pointer; }
  .genius-launcher:hover { transform: translateY(-2px); }
  .genius-panel { display: none; position: fixed; right: 1.2rem; bottom: 1.2rem; z-index: 121; width: min(360px, calc(100% - 2rem)); overflow: hidden; border: 1px solid rgba(0,0,0,.12); border-radius: 14px; background: #fff; box-shadow: 0 18px 50px rgba(0,0,0,.22); }
  .genius-panel.is-open { display: block; }
  .genius-panel__header { display: flex; align-items: center; justify-content: space-between; padding: 1rem; color: #fff; background: #090909; }
  .genius-panel__header strong { display: block; }
  .genius-panel__header small { color: #d4af5f; }
  .genius-panel__close { border: 0; color: #fff; background: transparent; font-size: 1.5rem; cursor: pointer; }
  .genius-panel__messages { display: grid; gap: .7rem; height: 280px; overflow-y: auto; padding: 1rem; background: #f7f2ea; }
  .genius-message { max-width: 88%; padding: .7rem .8rem; border-radius: 9px; line-height: 1.45; white-space: pre-line; }
  .genius-message--assistant { background: #fff; border: 1px solid rgba(0,0,0,.1); }
  .genius-message--visitor { justify-self: end; color: #fff; background: #090909; }
  .genius-panel__actions { display: flex; flex-wrap: wrap; gap: .45rem; padding: 0 1rem .8rem; background: #f7f2ea; }
  .genius-action { padding: .55rem .7rem; border: 1px solid #d4af5f; border-radius: 7px; color: #090909; background: #fff; font-size: .82rem; font-weight: 700; text-decoration: none; cursor: pointer; }
  .genius-action:hover { background: #d4af5f; }
  .genius-panel__form { display: flex; gap: .5rem; padding: .8rem; border-top: 1px solid rgba(0,0,0,.1); }
  .genius-panel__input { flex: 1; min-width: 0; padding: .7rem; border: 1px solid rgba(0,0,0,.15); border-radius: 7px; }
  .genius-panel__send { padding: .7rem .8rem; border: 0; border-radius: 7px; color: #090909; background: #d4af5f; font-weight: 700; cursor: pointer; }
  @media (max-width: 600px) { .genius-launcher { right: 1rem; bottom: 1rem; } .genius-panel { right: 1rem; bottom: 1rem; } }
`;
document.head.appendChild(assistantStyles);

const geniusLauncher = document.createElement('button');
geniusLauncher.className = 'genius-launcher';
geniusLauncher.type = 'button';
geniusLauncher.setAttribute('aria-label', 'Open Style Genius Brown');
geniusLauncher.title = 'Style Genius Brown';
geniusLauncher.textContent = 'SB';

const geniusPanel = document.createElement('section');
geniusPanel.className = 'genius-panel';
geniusPanel.setAttribute('aria-label', 'Style Genius Brown assistant');
geniusPanel.innerHTML = `
  <div class="genius-panel__header"><div><strong>Style Genius Brown</strong><small>R&B Fashion assistant</small></div><button type="button" class="genius-panel__close" aria-label="Close assistant">&times;</button></div>
  <div class="genius-panel__messages"></div>
  <div class="genius-panel__actions"></div>
  <form class="genius-panel__form"><input class="genius-panel__input" aria-label="Message Style Genius Brown" placeholder="Write a message..." autocomplete="off"><button class="genius-panel__send" type="submit">Send</button></form>
`;
document.body.appendChild(geniusLauncher);
document.body.appendChild(geniusPanel);

const geniusMessages = geniusPanel.querySelector('.genius-panel__messages');
const geniusActions = geniusPanel.querySelector('.genius-panel__actions');
const geniusInput = geniusPanel.querySelector('.genius-panel__input');
const geniusStorageKey = 'rb-style-genius-session';
let geniusState = readStoredJson(sessionStorage, geniusStorageKey, {
  stage: 'request',
  name: currentAccount?.name || '',
  messages: []
});
let geniusStage = currentAccount?.name ? 'request' : geniusState.stage;
let geniusName = currentAccount?.name || geniusState.name;

const saveGeniusState = () => {
  geniusState.stage = geniusStage;
  geniusState.name = geniusName;
  sessionStorage.setItem(geniusStorageKey, JSON.stringify(geniusState));
};

const addGeniusMessage = (message, type) => {
  const element = document.createElement('div');
  element.className = `genius-message genius-message--${type}`;
  element.textContent = message;
  geniusMessages.appendChild(element);
  geniusMessages.scrollTop = geniusMessages.scrollHeight;
  geniusState.messages.push({ message, type });
  saveGeniusState();
};

const addGeniusAction = (label, href) => {
  const link = document.createElement('a');
  link.className = 'genius-action';
  link.href = href;
  link.textContent = label;
  geniusActions.appendChild(link);
};

const addBagAction = () => {
  const bagAction = document.createElement('button');
  bagAction.className = 'genius-action';
  bagAction.type = 'button';
  bagAction.textContent = 'Open my bag';
  bagAction.addEventListener('click', () => document.querySelector('.header__actions a')?.click());
  geniusActions.appendChild(bagAction);
};

const openGenius = () => {
  geniusPanel.classList.add('is-open');
  geniusLauncher.style.display = 'none';
  if (!geniusMessages.children.length && geniusState.messages.length) {
    const savedMessages = [...geniusState.messages];
    geniusState.messages = [];
    savedMessages.forEach((item) => addGeniusMessage(item.message, item.type));
    addGeniusMessage(`Welcome back, ${geniusName}. We can continue from where we left off.`, 'assistant');
    addGeniusAction('Continue shopping', 'shop.html');
    addGeniusAction('Open Style Forum', 'forum.html');
  } else if (!geniusMessages.children.length) {
    addGeniusMessage(`Good day, ${geniusName}. I am Style Genius Brown. How may I assist you today?`, 'assistant');
  }
  geniusInput.focus();
};

geniusLauncher.addEventListener('click', openGenius);
geniusPanel.querySelector('.genius-panel__close').addEventListener('click', () => {
  geniusPanel.classList.remove('is-open');
  geniusLauncher.style.display = 'block';
});
geniusPanel.querySelector('.genius-panel__form').addEventListener('submit', (event) => {
  event.preventDefault();
  const message = geniusInput.value.trim();
  if (!message) return;
  addGeniusMessage(message, 'visitor');
  geniusInput.value = '';

  if (geniusStage === 'name') {
    geniusName = message;
    geniusStage = 'request';
    saveGeniusState();
    addGeniusMessage(`Thank you, ${geniusName}. How are you feeling today, and what would you like help finding?`, 'assistant');
    return;
  }

  const lowerMessage = message.toLowerCase();
  let response = `I understand, ${geniusName}. I will help you shape that look with care.`;
  geniusActions.innerHTML = '';
  if (lowerMessage.includes('all') || lowerMessage.includes('list') || lowerMessage.includes('catalog') || lowerMessage.includes('available') || lowerMessage.includes('what do you have')) {
    const catalogList = catalogProducts.map((product) => `${product.name} - ${formatMoney(getDiscountPrice(product))}`).join('\n');
    response = `Of course, ${geniusName}. Here is our current selection and the sale price for each item:\n\n${catalogList}\n\nChoose any item and I will guide you to its views and Bag options.`;
    addGeniusAction('Open Shop', 'shop.html');
    addGeniusAction('Browse Shoes', 'shoes.html');
    addGeniusAction('Request a custom look', 'forum.html');
  } else if (lowerMessage.includes('shoe') || lowerMessage.includes('sneaker') || lowerMessage.includes('asics') || lowerMessage.includes('boot')) {
    response += ' Our Shoes collection is a strong match: ASICS GEL runners for energy, platform sneakers for presence, and Dr. Martens for a tougher street finish.';
    addGeniusAction('Browse Shoes', 'shoes.html');
  } else if (lowerMessage.includes('formal') || lowerMessage.includes('suit') || lowerMessage.includes('dress')) {
    response += ' Our Formal wear edit is designed to look polished without feeling stiff: tailored suits, satin evening dresses, and clean-cut shirts.';
    addGeniusAction('View Formal wear', 'shop.html#formal-wear');
  } else if (lowerMessage.includes('baggy') || lowerMessage.includes('oversized') || lowerMessage.includes('street')) {
    response += ' The Sunyani street edit will fit that mood with baggy denim, oversized tees, varsity layers, and confident proportions.';
    addGeniusAction('Browse Streetwear', 'shop.html');
  } else {
    response += ' I can help you compare streetwear, sneakers, formalwear, and prices until the choice feels right.';
    addGeniusAction('Browse Shop', 'shop.html');
  }
  if (lowerMessage.includes('buy') || lowerMessage.includes('order') || lowerMessage.includes('price') || lowerMessage.includes('cost')) addBagAction();
  addGeniusAction('Request a custom look', 'forum.html');
  addGeniusMessage(response, 'assistant');
});

const galleryImages = {
  'Baggy blue denim': [
    'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?auto=format&fit=crop&w=900&q=80'
  ],
  'Baggy cargo denim': [
    'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=900&q=80'
  ],
  'Oversized graphic tee': [
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&w=900&q=80'
  ],
  'Oversized campus fit': [
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&w=900&q=80'
  ],
  'ASICS GEL street runners': [
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80'
  ],
  'Dr. Martens street boots': [
    'https://images.unsplash.com/photo-1608256246200-53e635b5b65f?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=80'
  ],
  'Platform street sneakers': [
    'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80'
  ],
  'Clean white low-tops': [
    'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80'
  ],
  'Tailored black suit': [
    'https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=900&q=80'
  ],
  'Satin evening dress': [
    'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=80'
  ],
  'Clean cut formal shirt': [
    'https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=900&q=80'
  ]
};

const galleryStyles = document.createElement('style');
galleryStyles.textContent = `
  .product-gallery { height: 100%; display: grid; grid-template-rows: 1fr auto; gap: 0.5rem; }
  .product-gallery__main { width: 100%; min-height: 0; height: 100%; object-fit: cover; background: #e9e3d8; }
  .product-gallery__thumbs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.35rem; padding: 0 0.5rem 0.5rem; }
  .product-gallery__thumb { height: 52px; padding: 0; border: 2px solid transparent; background: transparent; cursor: pointer; overflow: hidden; }
  .product-gallery__thumb.is-active { border-color: #d4af5f; }
  .product-gallery__thumb img { width: 100%; height: 100%; object-fit: cover; }
  .product__image .product-gallery { height: 100%; }
  .product__image .product-gallery__main { display: block; }
  .product-price__original { margin-right: 0.5rem; color: #888; text-decoration: line-through; font-weight: 400; }
  .product-price__sale { color: #b3261e; font-weight: 700; }
  .product-card, .product { cursor: pointer; }
  .product-viewer { display: none; position: fixed; inset: 0; z-index: 110; padding: 1rem; background: rgba(9, 9, 9, 0.92); color: #fff; }
  .product-viewer.is-open { display: grid; place-items: center; }
  .product-viewer__content { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 280px; width: min(1080px, 100%); max-height: calc(100vh - 2rem); overflow: auto; background: #181818; }
  .product-viewer__image { width: 100%; height: min(78vh, 720px); object-fit: contain; background: #111; }
  .product-viewer__details { padding: 2rem; align-self: center; }
  .product-viewer__category { color: #d4af5f; font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; }
  .product-viewer__name { margin: 0.5rem 0; font-size: clamp(1.5rem, 3vw, 2.4rem); }
  .product-viewer__price { margin: 0 0 1.5rem; color: #ddd; font-weight: 700; }
  .product-viewer__thumbs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4rem; }
  .product-viewer__thumb { height: 64px; padding: 0; border: 2px solid transparent; background: transparent; cursor: pointer; overflow: hidden; }
  .product-viewer__thumb.is-active { border-color: #d4af5f; }
  .product-viewer__thumb img { width: 100%; height: 100%; object-fit: cover; }
  .product-viewer__close, .product-viewer__arrow { position: absolute; z-index: 1; border: 0; color: #fff; background: rgba(0, 0, 0, 0.55); cursor: pointer; }
  .product-viewer__close { top: 0.75rem; right: 0.75rem; width: 40px; height: 40px; border-radius: 50%; font-size: 1.6rem; }
  .product-viewer__arrow { top: 50%; width: 42px; height: 42px; border-radius: 50%; font-size: 1.5rem; transform: translateY(-50%); }
  .product-viewer__arrow--previous { left: 0.75rem; }
  .product-viewer__arrow--next { right: calc(280px + 0.75rem); }
  @media (max-width: 760px) {
    .product-viewer__content { grid-template-columns: 1fr; }
    .product-viewer__image { height: 58vh; }
    .product-viewer__details { padding: 1.25rem; }
    .product-viewer__arrow--next { right: 0.75rem; }
  }
`;
document.head.appendChild(galleryStyles);

const initializeProductGalleries = () => document.querySelectorAll('.product, .product-card').forEach((product) => {
  const nameElement = product.querySelector('.product__name, .product-card__name');
  if (!nameElement) return;
  const imageHost = product.querySelector('.product__image, .product-card__image-wrapper');
  if (!imageHost) return;
  const images = imageHost.dataset.galleryImages
    ? JSON.parse(decodeURIComponent(imageHost.dataset.galleryImages))
    : galleryImages[nameElement.textContent.trim()];
  if (!images?.length || imageHost.querySelector('.product-gallery')) return;

  imageHost.classList.add('product-gallery-host');
  imageHost.style.backgroundImage = 'none';
  imageHost.innerHTML = `
    <div class="product-gallery">
      <img class="product-gallery__main" src="${escapeHtml(images[0])}" alt="${escapeHtml(nameElement.textContent.trim())} view 1" loading="lazy">
      <div class="product-gallery__thumbs" aria-label="More views of ${nameElement.textContent.trim()}">
        ${images.map((image, index) => `<button type="button" class="product-gallery__thumb ${index === 0 ? 'is-active' : ''}" data-gallery-image="${escapeHtml(image)}" aria-label="View ${index + 1} of ${escapeHtml(nameElement.textContent.trim())}"><img src="${escapeHtml(image)}" alt="" loading="lazy"></button>`).join('')}
      </div>
    </div>
  `;

  const mainImage = imageHost.querySelector('.product-gallery__main');
  imageHost.querySelectorAll('.product-gallery__thumb').forEach((thumb) => {
    thumb.addEventListener('click', () => {
      mainImage.src = thumb.dataset.galleryImage;
      mainImage.alt = `${nameElement.textContent.trim()} selected view`;
      imageHost.querySelectorAll('.product-gallery__thumb').forEach((item) => item.classList.remove('is-active'));
      thumb.classList.add('is-active');
    });
  });
});
initializeProductGalleries();

const productViewer = document.createElement('div');
productViewer.className = 'product-viewer';
productViewer.innerHTML = `
  <div class="product-viewer__content" role="dialog" aria-modal="true" aria-label="Product details">
    <button type="button" class="product-viewer__close" aria-label="Close product viewer">&times;</button>
    <button type="button" class="product-viewer__arrow product-viewer__arrow--previous" aria-label="Previous product view">&#8249;</button>
    <button type="button" class="product-viewer__arrow product-viewer__arrow--next" aria-label="Next product view">&#8250;</button>
    <img class="product-viewer__image" alt="">
    <div class="product-viewer__details">
      <span class="product-viewer__category"></span>
      <h2 class="product-viewer__name"></h2>
      <p class="product-viewer__price"></p>
      <p class="product-viewer__description"></p>
      <div class="product-viewer__thumbs" aria-label="Product views"></div>
    </div>
  </div>
`;
document.body.appendChild(productViewer);

const viewerImage = productViewer.querySelector('.product-viewer__image');
const viewerCategory = productViewer.querySelector('.product-viewer__category');
const viewerName = productViewer.querySelector('.product-viewer__name');
const viewerPrice = productViewer.querySelector('.product-viewer__price');
const viewerThumbs = productViewer.querySelector('.product-viewer__thumbs');
let viewerImages = [];
let viewerIndex = 0;

const showViewerImage = (index) => {
  viewerIndex = (index + viewerImages.length) % viewerImages.length;
  viewerImage.src = viewerImages[viewerIndex];
  viewerImage.alt = `${viewerName.textContent} view ${viewerIndex + 1}`;
  viewerThumbs.querySelectorAll('.product-viewer__thumb').forEach((thumb, thumbIndex) => {
    thumb.classList.toggle('is-active', thumbIndex === viewerIndex);
  });
};

const closeProductViewer = () => {
  productViewer.classList.remove('is-open');
  document.body.classList.remove('no-scroll');
};

document.addEventListener('click', (event) => {
  const product = event.target.closest('.product, .product-card');
  if (!product) return;
  if (event.target.closest('button')) return;
  const nameElement = product.querySelector('.product__name, .product-card__name');
  const categoryElement = product.querySelector('.product__tag, .product-card__category');
  const priceElement = product.querySelector('.product__price, .product-card__price');
  const imageHost = product.querySelector('[data-gallery-images]');
  const fallbackImage = galleryImages[nameElement.textContent.trim()];
  viewerImages = imageHost?.dataset.galleryImages
    ? JSON.parse(decodeURIComponent(imageHost.dataset.galleryImages))
    : fallbackImage || [];
  if (!viewerImages.length) return;
  viewerCategory.textContent = categoryElement.textContent.trim();
  viewerName.textContent = nameElement.textContent.trim();
  viewerPrice.textContent = `${formatMoney(Number(product.dataset.salePrice))} (was ${formatMoney(Number(product.dataset.originalPrice))})`;
  productViewer.querySelector('.product-viewer__description').textContent = product.dataset.description || '';
  viewerThumbs.innerHTML = viewerImages.map((image, index) => `<button type="button" class="product-viewer__thumb ${index === 0 ? 'is-active' : ''}" aria-label="View ${index + 1}"><img src="${escapeHtml(image)}" alt=""></button>`).join('');
  viewerThumbs.querySelectorAll('.product-viewer__thumb').forEach((thumb, index) => {
    thumb.addEventListener('click', () => showViewerImage(index));
  });
  showViewerImage(0);
  productViewer.classList.add('is-open');
  document.body.classList.add('no-scroll');
});

productViewer.querySelector('.product-viewer__close').addEventListener('click', closeProductViewer);
productViewer.querySelector('.product-viewer__arrow--previous').addEventListener('click', () => showViewerImage(viewerIndex - 1));
productViewer.querySelector('.product-viewer__arrow--next').addEventListener('click', () => showViewerImage(viewerIndex + 1));
productViewer.addEventListener('click', (event) => {
  if (event.target === productViewer) closeProductViewer();
});
document.addEventListener('keydown', (event) => {
  if (!productViewer.classList.contains('is-open')) return;
  if (event.key === 'Escape') closeProductViewer();
  if (event.key === 'ArrowLeft') showViewerImage(viewerIndex - 1);
  if (event.key === 'ArrowRight') showViewerImage(viewerIndex + 1);
});

const bagLink = document.querySelector('.header__actions a');
const bagBadge = document.querySelector('.badge, .header__badge');
const productButtons = [...document.querySelectorAll('.add-to-cart, .product__button')];
const bagStorageKey = 'rb-fashion-bag';
const getLocalBag = () => {
  try {
    return JSON.parse(localStorage.getItem(bagStorageKey) || '[]');
  } catch {
    localStorage.removeItem(bagStorageKey);
    return [];
  }
};
const saveLocalBag = (items) => localStorage.setItem(bagStorageKey, JSON.stringify(items));
let bagItems = getLocalBag();
const getBagProductName = (productElement) => {
  const element = productElement?.querySelector('.product-card__name, .product__name');
  return element ? element.textContent.trim() : 'Product';
};
const getBagProductPrice = (productElement) => {
  const salePrice = Number(productElement?.dataset.salePrice || productElement?.dataset.originalPrice || 0);
  return Number.isFinite(salePrice) ? salePrice : 0;
};
const mergeBagItem = (items, productId, productName, unitPrice, quantity = 1) => {
  const nextItems = [...items];
  const existingIndex = nextItems.findIndex((item) => String(item.id) === String(productId));
  const normalizedQuantity = Number(quantity) || 1;
  const normalizedPrice = Number(unitPrice) || 0;
  if (existingIndex >= 0) {
    nextItems[existingIndex] = {
      ...nextItems[existingIndex],
      name: productName || nextItems[existingIndex].name,
      amount: normalizedPrice || Number(nextItems[existingIndex].amount || 0),
      quantity: Number(nextItems[existingIndex].quantity || 0) + normalizedQuantity
    };
    return nextItems;
  }
  nextItems.push({
    id: productId,
    name: productName,
    amount: normalizedPrice,
    quantity: normalizedQuantity
  });
  return nextItems;
};

if (bagLink) {
  const bagPanel = document.createElement('div');
  bagPanel.className = 'bag-panel';
  bagPanel.innerHTML = `
    <aside class="bag-panel__content" role="dialog" aria-label="Shopping bag">
      <div class="bag-panel__header">
        <h2 class="bag-panel__title">Your bag</h2>
        <button type="button" class="bag-panel__close" aria-label="Close bag">&times;</button>
      </div>
      <div class="bag-panel__items"></div>
      <div class="bag-panel__total"></div>
      <p class="bag-panel__payment">Mobile Money payment numbers (choose either; manual confirmation): <a href="tel:+233547042682">0547042682</a> or <a href="tel:+233598585080">0598585080</a><br>WhatsApp support is also available at <a href="https://wa.me/233598585080" target="_blank" rel="noopener">0598585080</a>.<br>Send your order reference to <strong>brownkwame123@gmail.com</strong>.</p>
      <p class="bag-panel__status" aria-live="polite"></p>
      <form class="bag-panel__checkout" hidden>
        <label>Delivery name<input name="shippingName" required autocomplete="name"></label>
        <label>Phone number<input name="shippingPhone" required autocomplete="tel"></label>
        <label>Delivery address<textarea name="shippingAddress" required autocomplete="street-address"></textarea></label>
        <button type="submit">Place order</button>
      </form>
    </aside>
  `;
  document.body.appendChild(bagPanel);

  const bagItemsElement = bagPanel.querySelector('.bag-panel__items');
  const bagTotalElement = bagPanel.querySelector('.bag-panel__total');
  const bagStatusElement = bagPanel.querySelector('.bag-panel__status');
  const bagCheckoutForm = bagPanel.querySelector('.bag-panel__checkout');
  const bagCheckoutButton = bagCheckoutForm.querySelector('button[type="submit"]');
  bagCheckoutForm.elements.shippingName.value = currentAccount?.name || '';
  let serverCartEnabled = false;

  const updateBag = () => {
    saveLocalBag(bagItems);
    if (bagBadge) bagBadge.textContent = bagItems.reduce((sum, item) => sum + (item.quantity || 1), 0);
    const canCheckout = Boolean(currentAccount?.token) && serverCartEnabled && bagItems.length > 0;
    bagCheckoutForm.hidden = !canCheckout;

    if (bagItems.length === 0) {
      bagItemsElement.innerHTML = '<p class="bag-panel__empty">Your bag is empty.</p>';
      bagTotalElement.innerHTML = '';
      return;
    }

    bagItemsElement.replaceChildren();
    bagItems.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'bag-panel__item';
      const details = document.createElement('div');
      const name = document.createElement('p');
      name.className = 'bag-panel__item-name';
      name.textContent = item.name;
      const price = document.createElement('p');
      price.className = 'bag-panel__item-price';
      price.textContent = `${formatMoney(item.amount)} x ${item.quantity || 1}`;
      details.append(name, price);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'bag-panel__remove';
      remove.dataset.bagIndex = index;
      remove.textContent = 'Remove';
      row.append(details, remove);
      bagItemsElement.append(row);
    });

    const total = bagItems.reduce((sum, item) => sum + item.amount * (item.quantity || 1), 0);
    bagTotalElement.innerHTML = `<span>Total</span><span>GH₵ ${total}</span>`;
  };

  const syncBagFromServer = async () => {
    if (!currentAccount?.token) {
      serverCartEnabled = false;
      updateBag();
      return true;
    }
    try {
      const response = await backendRequest('/cart');
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Your live bag is unavailable.');
      const serverItems = result.items.map((item) => ({
        id: item.product_id,
        name: item.name,
        amount: item.unitPrice,
        quantity: item.quantity
      }));
      bagItems = serverItems.length ? serverItems : getLocalBag();
      serverCartEnabled = true;
      updateBag();
      return true;
    } catch (error) {
      bagStatusElement.textContent = error.message || 'Could not connect to your live bag. Please try again.';
      return false;
    }
  };

  const closeBag = () => bagPanel.classList.remove('is-open');

  bagLink.addEventListener('click', (event) => {
    event.preventDefault();
    updateBag();
    bagPanel.classList.add('is-open');
    syncBagFromServer();
  });
  bagPanel.querySelector('.bag-panel__close').addEventListener('click', closeBag);
  bagPanel.addEventListener('click', (event) => {
    if (event.target === bagPanel) closeBag();
    const removeButton = event.target.closest('[data-bag-index]');
    if (!removeButton) return;
    const itemIndex = Number(removeButton.dataset.bagIndex);
    const item = bagItems[itemIndex];
    if (!item) return;
    if (!serverCartEnabled || !currentAccount?.token || !item.id) {
      bagItems.splice(itemIndex, 1);
      bagStatusElement.textContent = '';
      updateBag();
      return;
    }
    backendRequest(`/cart/items/${encodeURIComponent(item.id)}`, { method: 'DELETE' })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not remove this item from your bag.');
        await syncBagFromServer();
        bagStatusElement.textContent = '';
      })
      .catch((error) => { bagStatusElement.textContent = error.message; });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeBag();
  });

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('.add-to-cart, .product__button');
    if (!button || button.disabled) return;
    const product = button.closest('.product, .product-card');
    if (!product) return;
    const productId = product.dataset.productId;
    if (!productId) {
      bagStatusElement.textContent = 'This product is missing its store inventory record.';
      return;
    }
    bagPanel.classList.add('is-open');
    if (currentAccount?.token) {
      if (!serverCartEnabled && !(await syncBagFromServer())) return;
      try {
        const response = await backendRequest('/cart/items', {
          method: 'POST',
          body: JSON.stringify({ productId, quantity: 1 })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not add this item to your bag.');
        bagItems = result.items.map((item) => ({
          id: item.product_id,
          name: item.name,
          amount: item.unitPrice,
          quantity: item.quantity
        }));
        updateBag();
        bagStatusElement.textContent = 'Added to your bag.';
        return;
      } catch (error) {
        bagStatusElement.textContent = error.message;
        return;
      }
    }
    bagItems = mergeBagItem(
      bagItems,
      productId,
      getBagProductName(product),
      getBagProductPrice(product),
      1
    );
    updateBag();
    bagStatusElement.textContent = 'Added to your bag.';
  });

  bagCheckoutForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!serverCartEnabled) return;
    const fields = new FormData(bagCheckoutForm);
    bagCheckoutButton.disabled = true;
    bagStatusElement.textContent = 'Submitting your order...';
    try {
      const orderResponse = await backendRequest('/orders', {
        method: 'POST',
        body: JSON.stringify({
          shipping: {
            name: fields.get('shippingName'),
            phone: fields.get('shippingPhone'),
            address: fields.get('shippingAddress')
          }
        })
      });
      const orderResult = await orderResponse.json();
      if (!orderResponse.ok) throw new Error(orderResult.error || 'Could not place this order.');

      const paymentResponse = await backendRequest('/payments/checkout', {
        method: 'POST',
        body: JSON.stringify({ orderId: orderResult.order.id })
      });
      const paymentResult = await paymentResponse.json();
      if (!paymentResponse.ok) throw new Error(paymentResult.error || 'Could not prepare payment instructions.');

      await syncBagFromServer();
      bagStatusElement.textContent = `Order ${orderResult.order.id} created.\n${paymentResult.instructions}\nReference: ${paymentResult.reference}`;
      bagCheckoutForm.reset();
      bagCheckoutForm.elements.shippingName.value = currentAccount?.name || '';
    } catch (error) {
      bagStatusElement.textContent = error.message;
    } finally {
      bagCheckoutButton.disabled = false;
    }
  });

  updateBag();
  syncBagFromServer();
}

const menuToggle = document.querySelector('.header__menu-toggle');
const navMobile = document.querySelector('.nav-mobile');
const navOverlay = document.querySelector('.nav-overlay');
const mobileClose = document.querySelector('.nav-mobile__close');

if (menuToggle && navMobile && navOverlay) {
  menuToggle.addEventListener('click', () => {
    const isOpen = navMobile.classList.toggle('open');
    navOverlay.classList.toggle('active', isOpen);
    menuToggle.classList.toggle('active', isOpen);
    menuToggle.setAttribute('aria-expanded', String(isOpen));
    document.body.classList.toggle('no-scroll', isOpen);
  });

  navOverlay.addEventListener('click', () => {
    navMobile.classList.remove('open');
    navOverlay.classList.remove('active');
    menuToggle.classList.remove('active');
    menuToggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('no-scroll');
  });

  if (mobileClose) {
    mobileClose.addEventListener('click', () => {
      navMobile.classList.remove('open');
      navOverlay.classList.remove('active');
      menuToggle.classList.remove('active');
      menuToggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('no-scroll');
    });
  }
}

backendRequest('/products')
  .then(async (response) => {
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not load the live product catalog.');
    if (!Array.isArray(result.products)) throw new Error('The product catalog response is invalid.');
    catalogProducts = result.products.map(mapApiProduct);
    renderCatalogGrids();
    initializeProductGalleries();
    const searchInput = document.querySelector('#site-search');
    searchInput?.dispatchEvent(new Event('input'));
    if (window.location.hash.startsWith('#product-')) {
      document.getElementById(window.location.hash.slice(1))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  })
  .catch((error) => {
    document.querySelectorAll('[data-catalog]').forEach((grid) => {
      if (grid.querySelector('.catalog-connectivity-status')) return;
      const status = document.createElement('p');
      status.className = 'catalog-connectivity-status';
      status.setAttribute('role', 'status');
      status.textContent = 'Live inventory is unavailable. Product prices and stock may be out of date; ordering is temporarily unavailable.';
      grid.prepend(status);
    });
    console.error('Live product catalog unavailable:', error);
  });
