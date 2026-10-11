const API_URL = window.location.protocol === 'file:'
  ? 'http://127.0.0.1:8000/api'
  : '/api';

const accountKey = 'rb-account';
let account;
try {
  account = JSON.parse(localStorage.getItem(accountKey) || 'null');
} catch {
  localStorage.removeItem(accountKey);
  account = null;
}
let allProducts = [];

const productForm = document.getElementById('productForm');
const productRows = document.getElementById('productRows');
const orderRows = document.getElementById('orderRows');
const productCount = document.getElementById('productCount');
const formStatus = document.getElementById('formStatus');
const listStatus = document.getElementById('listStatus');
const ordersStatus = document.getElementById('ordersStatus');
const accessStatus = document.getElementById('accessStatus');
const emptyState = document.getElementById('emptyState');
const ordersEmptyState = document.getElementById('ordersEmptyState');
const refreshButton = document.getElementById('refreshProducts');
const refreshOrdersButton = document.getElementById('refreshOrders');
const signOutButton = document.getElementById('signOutButton');
const saveProductButton = document.getElementById('saveProduct');
const cancelEditButton = document.getElementById('cancelEdit');
const imageFileInput = productForm.elements.imageFile;
const imageUploadStatus = document.getElementById('imageUploadStatus');
const maxImageSize = 700_000;

const orderStatuses = [
  ['pending_payment', 'Pending payment'],
  ['paid', 'Paid'],
  ['processing', 'Processing'],
  ['packed', 'Packed'],
  ['shipped', 'Shipped'],
  ['delivered', 'Delivered'],
  ['cancelled', 'Cancelled'],
  ['refunded', 'Refunded']
];

const setMessage = (element, message = '', isError = false) => {
  element.textContent = message;
  element.classList.toggle('is-error', isError);
};

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[character]));

const money = (value) => `GH₵ ${Number(value || 0).toLocaleString()}`;

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${account?.token || ''}`,
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}

function resetProductForm() {
  productForm.reset();
  delete productForm.dataset.editingId;
  productForm.elements.id.readOnly = false;
  saveProductButton.textContent = 'Add product';
  cancelEditButton.hidden = true;
  setMessage(formStatus);
  imageUploadStatus.textContent = 'JPEG, PNG, WebP, or GIF. Maximum 700 KB.';
}

function readImageFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener('load', () => resolve(reader.result));
    reader.addEventListener('error', () => reject(new Error('Could not read the selected image.')));
    reader.readAsDataURL(file);
  });
}

function renderProducts(products) {
  allProducts = products;
  const activeProducts = products.filter((product) => product.active);
  productCount.textContent = activeProducts.length;
  emptyState.hidden = products.length !== 0;

  productRows.innerHTML = products.map((product) => `
    <tr>
      <td>
        <span class="product-name">${escapeHtml(product.name)}</span>
        <span class="product-id">${escapeHtml(product.id)}</span>
      </td>
      <td data-label="Category">${escapeHtml(product.category)}</td>
      <td data-label="Price">${money(product.price)}</td>
      <td data-label="Stock">${Number(product.stock)}</td>
      <td data-label="Visibility">${product.active ? 'Visible' : 'Archived'}</td>
      <td class="product-actions" data-label="Actions">
        <button class="edit-button" type="button" data-edit-product="${escapeHtml(product.id)}">Edit</button>
        <button class="delete-button" type="button" data-product-id="${escapeHtml(product.id)}" data-active="${Boolean(product.active)}">
          ${product.active ? 'Archive' : 'Restore'}
        </button>
      </td>
    </tr>
  `).join('');
}

async function loadProducts() {
  refreshButton.disabled = true;
  setMessage(listStatus, 'Loading products…');
  try {
    const data = await api('/admin/products');
    renderProducts(data.products || []);
    setMessage(listStatus);
  } catch (error) {
    setMessage(listStatus, error.message, true);
  } finally {
    refreshButton.disabled = false;
  }
}

function renderOrders(orders) {
  ordersEmptyState.hidden = orders.length !== 0;
  document.getElementById('ordersCount').textContent = `${orders.length} total`;
  document.getElementById('ordersRevenue').textContent = money(
    orders.filter((order) => ['paid', 'processing', 'packed', 'shipped', 'delivered'].includes(order.status))
      .reduce((sum, order) => sum + Number(order.total || 0), 0)
  );
  orderRows.innerHTML = orders.map((order) => {
    const orderItems = (order.items || []).map((item) =>
      `${escapeHtml(item.name)} × ${Number(item.quantity)}`
    ).join('<br>');
    const shipping = [
      order.shipping_name,
      order.shipping_phone,
      order.shipping_address
    ].filter(Boolean).map(escapeHtml).join('<br>');
    const date = order.created_at ? new Date(`${order.created_at.replace(' ', 'T')}Z`).toLocaleString() : '';
    const statuses = orderStatuses.map(([value, label]) =>
      `<option value="${value}" ${order.status === value ? 'selected' : ''}>${label}</option>`
    ).join('');
    return `
      <tr>
        <td data-label="Order"><strong>#${Number(order.id)}</strong><span class="product-id">${escapeHtml(date)}</span></td>
        <td data-label="Customer / delivery"><strong>${escapeHtml(order.customer_name)}</strong><br><a href="mailto:${escapeHtml(order.customer_email)}">${escapeHtml(order.customer_email)}</a><br>${shipping}</td>
        <td data-label="Items">${orderItems || '—'}</td>
        <td data-label="Total">${money(order.total)}</td>
        <td data-label="Payment">${escapeHtml(order.payment_reference || 'Not generated')}<span class="product-id">${escapeHtml(order.payment_status || 'Unpaid')}</span></td>
        <td data-label="Status">
          <select class="order-status" data-order-id="${Number(order.id)}" data-current-status="${escapeHtml(order.status)}" aria-label="Status for order ${Number(order.id)}">
            ${statuses}
          </select>
        </td>
      </tr>
    `;
  }).join('');
}

async function loadOrders() {
  refreshOrdersButton.disabled = true;
  setMessage(ordersStatus, 'Loading orders…');
  try {
    const data = await api('/admin/orders');
    renderOrders(data.orders || []);
    setMessage(ordersStatus);
  } catch (error) {
    setMessage(ordersStatus, error.message, true);
  } finally {
    refreshOrdersButton.disabled = false;
  }
}

async function confirmAdminAccess() {
  if (!account?.token) {
    setMessage(accessStatus, 'Sign in with your administrator account to manage this store.', true);
    return false;
  }
  try {
    const data = await api('/me');
    if (data.user.role !== 'admin') {
      throw new Error('Administrator access is required. Set RB_ADMIN_EMAIL for the trusted owner account before registering it.');
    }
    account = { ...account, ...data.user };
    localStorage.setItem(accountKey, JSON.stringify(account));
    setMessage(accessStatus, `Signed in as store administrator ${account.name}.`);
    return true;
  } catch (error) {
    localStorage.removeItem(accountKey);
    account = null;
    setMessage(accessStatus, error.message, true);
    setTimeout(() => {
      window.location.href = 'account.html';
    }, 800);
    return false;
  }
}

productForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const fields = new FormData(productForm);
  const product = {
    id: String(fields.get('id')).trim(),
    name: String(fields.get('name')).trim(),
    category: fields.get('category'),
    price: Number(fields.get('price')),
    stock: Number(fields.get('stock')),
    imageUrl: String(fields.get('imageUrl')).trim(),
    description: String(fields.get('description')).trim(),
    active: true
  };
  const imageFile = fields.get('imageFile');
  const editingId = productForm.dataset.editingId;
  const submitButton = productForm.querySelector('button[type="submit"]');
  setMessage(formStatus);
  submitButton.disabled = true;
  try {
    if (imageFile?.size) {
      if (imageFile.size > maxImageSize) throw new Error('Choose an image smaller than 700 KB.');
      setMessage(formStatus, 'Uploading image…');
      const imageData = await readImageFile(imageFile);
      const uploadedImage = await api('/admin/uploads', {
        method: 'POST',
        body: JSON.stringify({ imageData })
      });
      product.imageUrl = uploadedImage.imageUrl;
    }
    await api(editingId
      ? `/admin/products/${encodeURIComponent(editingId)}`
      : '/admin/products', {
      method: editingId ? 'PUT' : 'POST',
      body: JSON.stringify(product)
    });
    resetProductForm();
    setMessage(formStatus, editingId ? 'Product updated and visible in the shop.' : 'Product added and visible in the shop.');
    await loadProducts();
  } catch (error) {
    setMessage(formStatus, error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

productRows.addEventListener('click', async (event) => {
  const editButton = event.target.closest('[data-edit-product]');
  if (editButton) {
    const product = allProducts.find((item) => item.id === editButton.dataset.editProduct);
    if (!product) return;
    for (const [name, value] of Object.entries({
      id: product.id,
      name: product.name,
      category: product.category,
      price: product.price,
      stock: product.stock,
      imageUrl: product.image_url || '',
      description: product.description || ''
    })) productForm.elements[name].value = value;
    productForm.dataset.editingId = product.id;
    productForm.elements.id.readOnly = true;
    saveProductButton.textContent = 'Save changes';
    cancelEditButton.hidden = false;
    setMessage(formStatus, `Editing ${product.name}${product.active ? '' : ' (archived; saving will restore it)'}.`);
    productForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  const button = event.target.closest('[data-product-id]');
  if (!button) return;
  const productId = button.dataset.productId;
  const wasActive = button.dataset.active === 'true';
  if (wasActive && !window.confirm('Archive this product from the shop? Past orders will be kept.')) return;

  button.disabled = true;
  try {
    if (wasActive) {
      await api(`/admin/products/${encodeURIComponent(productId)}`, { method: 'DELETE' });
    } else {
      const product = allProducts.find((item) => item.id === productId);
      if (!product) throw new Error('Product is no longer in the inventory list.');
      await api(`/admin/products/${encodeURIComponent(productId)}`, {
        method: 'PUT',
        body: JSON.stringify({
          id: product.id,
          name: product.name,
          category: product.category,
          price: product.price,
          stock: product.stock,
          imageUrl: product.image_url || '',
          description: product.description || '',
          active: true
        })
      });
    }
    setMessage(listStatus, wasActive ? 'Product archived.' : 'Product restored to the shop.');
    await loadProducts();
  } catch (error) {
    setMessage(listStatus, error.message, true);
    button.disabled = false;
  }
});

orderRows.addEventListener('change', async (event) => {
  const select = event.target.closest('[data-order-id]');
  if (!select) return;
  const previousStatus = select.dataset.currentStatus || select.value;
  if (select.value === 'paid' && previousStatus !== 'paid'
    && !window.confirm('Only mark this order paid after verifying the Mobile Money payment to either 0547042682 or 0598585080. Continue?')) {
    select.value = previousStatus;
    return;
  }
  select.disabled = true;
  setMessage(ordersStatus, 'Updating order…');
  try {
    await api(`/admin/orders/${encodeURIComponent(select.dataset.orderId)}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status: select.value })
    });
    setMessage(ordersStatus, 'Order status updated.');
    await loadOrders();
  } catch (error) {
    setMessage(ordersStatus, error.message, true);
    select.value = previousStatus;
    select.disabled = false;
  }
});

refreshButton.addEventListener('click', loadProducts);
refreshOrdersButton.addEventListener('click', loadOrders);
cancelEditButton.addEventListener('click', resetProductForm);
imageFileInput.addEventListener('change', () => {
  const file = imageFileInput.files[0];
  if (!file) {
    imageUploadStatus.textContent = 'JPEG, PNG, WebP, or GIF. Maximum 700 KB.';
  } else if (file.size > maxImageSize) {
    imageFileInput.value = '';
    imageUploadStatus.textContent = 'That image is too large. Choose a file smaller than 700 KB.';
  } else {
    imageUploadStatus.textContent = `Selected: ${file.name}`;
  }
});

signOutButton.addEventListener('click', async () => {
  try {
    await api('/auth/logout', { method: 'POST' });
  } catch (error) {
    console.error('Could not revoke the server session during sign-out:', error);
  } finally {
    localStorage.removeItem(accountKey);
    account = null;
    window.location.href = 'account.html';
  }
});

(async () => {
  if (await confirmAdminAccess()) {
    await Promise.all([loadProducts(), loadOrders()]);
  }
})();
