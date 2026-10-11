const requestForm = document.querySelector('#styleRequestForm');
const requestImage = document.querySelector('#requestImage');
const uploadPreview = document.querySelector('#uploadPreview');
const forumChat = document.querySelector('#forumChat');
const handoffMessage = document.querySelector('#handoffMessage');
let signedInAccount;
try {
  signedInAccount = JSON.parse(localStorage.getItem('rb-account') || 'null');
} catch {
  localStorage.removeItem('rb-account');
  signedInAccount = null;
}

if (signedInAccount?.name) {
  const accountNameInput = document.querySelector('#requestName');
  accountNameInput.value = signedInAccount.name;
  accountNameInput.readOnly = true;
  accountNameInput.closest('.field').querySelector('label').textContent = 'Account name';
}

let uploadedImageData = '';

const feelingQuotes = {
  confident: 'Confidence is your best look; let your outfit make room for it.',
  calm: 'A calm mind deserves a clean silhouette and an effortless finish.',
  tired: 'Even on a difficult day, one thoughtful detail can bring your energy back.',
  excited: 'Keep that excitement close; the right look should feel like a beginning.',
  unsure: 'You do not need all the answers today; we can find your next look together.'
};

const getFeelingQuote = (feeling) => {
  const words = feeling.toLowerCase();
  if (words.includes('confident') || words.includes('good') || words.includes('ready')) return feelingQuotes.confident;
  if (words.includes('calm') || words.includes('focused') || words.includes('peace')) return feelingQuotes.calm;
  if (words.includes('tired') || words.includes('sad') || words.includes('stress')) return feelingQuotes.tired;
  if (words.includes('excited') || words.includes('happy') || words.includes('joy')) return feelingQuotes.excited;
  return feelingQuotes.unsure;
};

const addForumMessage = (message, type) => {
  const element = document.createElement('div');
  element.className = `chat-message chat-message--${type}`;
  const label = document.createElement('span');
  label.className = 'chat-message__label';
  label.textContent = type === 'bot' ? 'Style Genius Brown' : 'You';
  const content = document.createElement('span');
  content.textContent = message;
  element.append(label, content);
  forumChat.appendChild(element);
  forumChat.scrollTop = forumChat.scrollHeight;
};

requestImage.addEventListener('change', () => {
  const file = requestImage.files[0];
  if (!file) return;
  if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type) || file.size > 700_000) {
    handoffMessage.textContent = 'Choose a JPEG, PNG, WebP, or GIF image no larger than 700 KB.';
    handoffMessage.classList.add('is-visible');
    requestImage.value = '';
    uploadedImageData = '';
    uploadPreview.removeAttribute('src');
    uploadPreview.style.display = 'none';
    return;
  }
  const reader = new FileReader();
  reader.addEventListener('load', () => {
    uploadedImageData = reader.result;
    uploadPreview.src = uploadedImageData;
    uploadPreview.style.display = 'block';
  });
  reader.addEventListener('error', () => {
    handoffMessage.textContent = 'The selected image could not be read. Please choose it again.';
    handoffMessage.classList.add('is-visible');
  });
  reader.readAsDataURL(file);
});

const stepFields = [
  document.querySelector('#requestName').closest('.field'),
  document.querySelector('#requestFeeling').closest('.field'),
  document.querySelector('#requestType').closest('.field'),
  document.querySelector('#requestMessage').closest('.field'),
  document.querySelector('#requestContact').closest('.field'),
  document.querySelector('#requestImage').closest('.field')
];
let currentStep = 0;
requestForm.noValidate = true;
stepFields.forEach((field, index) => {
  field.hidden = index !== 0;
});

const submitButton = requestForm.querySelector('button[type="submit"]');
const revealNextStep = () => {
  currentStep += 1;
  if (stepFields[currentStep]) {
    stepFields[currentStep].hidden = false;
    stepFields[currentStep].querySelector('input, select, textarea').focus();
    submitButton.textContent = currentStep === stepFields.length - 1 ? 'Send request to R&B' : 'Continue';
  }
};

const finishRequest = async () => {
  const formData = new FormData(requestForm);
  const name = formData.get('name').trim();
  const contact = formData.get('contact').trim();
  const feeling = formData.get('feeling');
  const type = formData.get('type');
  const message = formData.get('message').trim();
  const request = {
    id: `RB-${Date.now().toString().slice(-6)}`,
    name,
    contact,
    feeling,
    type,
    message,
    image: uploadedImageData,
    createdAt: new Date().toISOString()
  };
  const apiUrl = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000/api' : '/api';
  const session = JSON.parse(localStorage.getItem('rb-account') || 'null');
  if (session?.token) {
    submitButton.disabled = true;
    try {
      const response = await fetch(`${apiUrl}/forum-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ feeling, type, message, contact, imageData: uploadedImageData })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Your request could not be sent.');
    } catch (error) {
      handoffMessage.textContent = `${error.message} Please try again or contact the R&B team directly.`;
      handoffMessage.classList.add('is-visible');
      submitButton.disabled = false;
      return;
    }
  }

  localStorage.setItem('rb-latest-style-request', JSON.stringify(request));
  const subject = `Style request ${request.id}: ${type}`;
  const body = `Name: ${name}\nContact: ${contact}\nRequest type: ${type}\nDetails: ${message}\n\nReference image uploaded: ${uploadedImageData ? 'Yes; included with the signed-in request' : 'No'}`;
  const strong = document.createElement('strong');
  strong.textContent = `Request ${request.id} is ready for R&B.`;
  const details = document.createElement('p');
  details.textContent = session?.token
    ? 'Your request was saved. Use the link below to email a copy to the team.'
    : 'Click below to forward the details to the team. Sign in to save requests and image uploads to your account.';
  const emailLink = document.createElement('a');
  emailLink.href = `mailto:brownkwame123@gmail.com?${new URLSearchParams({ subject, body })}`;
  emailLink.textContent = 'Forward to R&B team';
  handoffMessage.replaceChildren(strong, details, emailLink);
  handoffMessage.classList.add('is-visible');
  submitButton.textContent = 'Request sent';
  submitButton.disabled = true;
};

requestForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const activeField = stepFields[currentStep].querySelector('input, select, textarea');
  if (activeField.required && !activeField.value.trim()) {
    activeField.focus();
    return;
  }

  const formData = new FormData(requestForm);
  const name = formData.get('name').trim();
  const feeling = formData.get('feeling');
  const type = formData.get('type');
  const message = formData.get('message').trim();

  if (currentStep === 0) {
    addForumMessage(`Good day, ${name}. How are you feeling today?`, 'bot');
  } else if (currentStep === 1) {
    const quote = getFeelingQuote(feeling);
    addForumMessage(`${name}, thank you for sharing that you are feeling ${feeling}. ${quote}`, 'bot');
  } else if (currentStep === 2) {
    addForumMessage(`${name}, understood. Let us find the right ${type.toLowerCase()} for you.`, 'bot');
  } else if (currentStep === 3) {
    addForumMessage(`${name}, I have noted your request: “${message}”. Please share the best way for the R&B team to reach you.`, 'bot');
  } else if (currentStep === 4) {
    addForumMessage(`${name}, thank you. You may now add a reference image, or continue without one.`, 'bot');
  } else {
    await finishRequest();
    return;
  }

  revealNextStep();
});
