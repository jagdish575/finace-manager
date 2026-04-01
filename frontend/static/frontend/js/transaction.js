const API_BASE = '/api/transactions/';
let transactionsData = [];
let currentPage = 1;
const rowsPerPage = 8;
let sortField = null;
let sortDirection = 'asc';

function safeQuery(selector) {
    return document.querySelector(selector);
}

function getCookie(name) {
    const cookies = document.cookie.split(';').map(cookie => cookie.trim());
    const match = cookies.find(cookie => cookie.startsWith(name + '='));
    return match ? decodeURIComponent(match.split('=')[1]) : null;
}

function getCsrfToken() {
    return getCookie('csrftoken');
}

function openModal() {
    const modal = safeQuery('#addTransactionModal');
    modal?.classList.remove('hidden');
}

function closeModal() {
    const modal = safeQuery('#addTransactionModal');
    modal?.classList.add('hidden');
}

async function addTransaction(event) {
    event.preventDefault();

    const newTransaction = {
        date: safeQuery('#transactionDate')?.value,
        category_id: safeQuery('#transactionCategory')?.value,
        amount: parseFloat(safeQuery('#transactionAmount')?.value || 0),
        currency: safeQuery('#transactionCurrency')?.value,
        description: safeQuery('#transactionDescription')?.value,
    };

    try {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(newTransaction),
            credentials: 'same-origin',
        });

        if (!response.ok) {
            console.error('Failed to add transaction', response.status);
            alert('Unable to save transaction. Please refresh the page and try again.');
            return;
        }

        await fetchTransactions();
        closeModal();
        event.target.reset();
    } catch (error) {
        console.error('Error adding transaction:', error);
    }
}

function getFilteredTransactions() {
    const dateValue = safeQuery('#filterDate')?.value;
    const categoryValue = safeQuery('#filterCategory')?.value;
    const minAmountValue = parseFloat(safeQuery('#filterAmount')?.value || '');
    const searchValue = safeQuery('#searchText')?.value.toLowerCase();

    return transactionsData.filter((transaction) => {
        if (dateValue && transaction.date !== dateValue) return false;
        if (categoryValue && transaction.category_type.toLowerCase() !== categoryValue.toLowerCase() && transaction.category_name?.toLowerCase() !== categoryValue.toLowerCase()) return false;
        if (!Number.isNaN(minAmountValue) && minAmountValue !== '' && transaction.amount < minAmountValue) return false;
        if (searchValue && !transaction.description?.toLowerCase().includes(searchValue)) return false;
        return true;
    });
}

function sortTransactions(field) {
    if (sortField === field) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortField = field;
        sortDirection = 'asc';
    }
    renderTransactions();
}

function changePage(direction) {
    const filtered = getFilteredTransactions();
    const totalPages = Math.max(1, Math.ceil(filtered.length / rowsPerPage));
    currentPage = Math.min(Math.max(1, currentPage + direction), totalPages);
    renderTransactions();
}

async function fetchTransactions() {
    try {
        const response = await fetch(API_BASE);
        const transactions = await response.json();
        transactionsData = Array.isArray(transactions) ? transactions : [];
        currentPage = 1;
        renderTransactions();
    } catch (error) {
        console.error('Error fetching transactions:', error);
    }
}

function renderTransactions() {
    const tbody = safeQuery('#transactionsList');
    const countEl = safeQuery('#transactionCount');
    const currentPageEl = safeQuery('#currentPage');
    const totalPagesEl = safeQuery('#totalPages');

    let filtered = getFilteredTransactions();

    if (sortField) {
        filtered.sort((a, b) => {
            const aValue = a[sortField] ?? '';
            const bValue = b[sortField] ?? '';
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
            }
            return sortDirection === 'asc'
                ? String(aValue).localeCompare(String(bValue))
                : String(bValue).localeCompare(String(aValue));
        });
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / rowsPerPage));
    currentPage = Math.min(Math.max(1, currentPage), totalPages);
    const startIndex = (currentPage - 1) * rowsPerPage;
    const paged = filtered.slice(startIndex, startIndex + rowsPerPage);

    tbody.innerHTML = paged.map((t) => `
        <tr class="border-b last:border-b-0">
            <td class="px-4 py-4 text-slate-700">${t.date || '-'}</td>
            <td class="px-4 py-4 text-slate-700">${t.category_type || t.category_name || '-'}</td>
            <td class="px-4 py-4 text-right font-semibold text-slate-900">${typeof t.amount === 'number' ? '$' + t.amount.toFixed(2) : t.amount}</td>
            <td class="px-4 py-4 text-slate-700">${t.currency || '-'}</td>
            <td class="px-4 py-4 text-slate-700">${t.description || '-'}</td>
            <td class="px-4 py-4 text-center">
                <button onclick="deleteTransaction(${t.id})" class="rounded-full bg-red-50 px-3 py-1 text-sm font-semibold text-red-600 transition hover:bg-red-100">Delete</button>
            </td>
        </tr>
    `).join('');

    countEl.textContent = filtered.length;
    currentPageEl.textContent = currentPage;
    totalPagesEl.textContent = totalPages;
}

async function deleteTransaction(transactionId) {
    try {
        await fetch(`${API_BASE}${transactionId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
        });
        await fetchTransactions();
    } catch (error) {
        console.error('Error deleting transaction:', error);
    }
}

function exportCsv() {
    window.location.href = '/api/transactions/export-transactions-csv/';
}

function initializeVoiceInput() {
    const voiceEntryBtn = safeQuery('#voiceEntryBtn');
    if (!voiceEntryBtn) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    voiceEntryBtn.addEventListener('click', () => {
        recognition.start();
        voiceEntryBtn.textContent = 'Listening...';
    });

    recognition.onresult = async (event) => {
        const voiceText = event.results[0][0].transcript;
        voiceEntryBtn.textContent = 'Voice Input';

        try {
            const response = await fetch('/api/process-voice-entry/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voice_text: voiceText }),
            });
            const data = await response.json();
            if (data.error) {
                alert('Error processing voice input.');
                return;
            }
            openModal();
            safeQuery('#transactionAmount').value = data.amount || '';
            safeQuery('#transactionDescription').value = data.description || voiceText || '';
        } catch (error) {
            console.error('Voice processing error:', error);
            alert('Error processing voice input.');
        }
    };

    recognition.onerror = (event) => {
        voiceEntryBtn.textContent = 'Voice Input';
        alert('Voice recognition error: ' + event.error);
    };
}

function setupModalEvents() {
    const addTransactionBtn = safeQuery('#addTransactionBtn');
    const closeModalBtn = safeQuery('#closeModal');
    const closeModalBottomBtn = safeQuery('#closeModalBottom');
    const modalOverlay = safeQuery('#addTransactionModal');
    const transactionForm = safeQuery('#transactionForm');

    addTransactionBtn?.addEventListener('click', openModal);
    closeModalBtn?.addEventListener('click', closeModal);
    closeModalBottomBtn?.addEventListener('click', closeModal);
    transactionForm?.addEventListener('submit', addTransaction);
    modalOverlay?.addEventListener('click', (event) => {
        if (event.target === modalOverlay) closeModal();
    });
}

function initializePage() {
    setupModalEvents();
    initializeVoiceInput();
    safeQuery('#exportCsvBtn')?.addEventListener('click', exportCsv);
    fetchTransactions();
}

document.addEventListener('DOMContentLoaded', initializePage);

    