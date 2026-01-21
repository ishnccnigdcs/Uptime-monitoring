// Глобальные переменные
let sites = [];
let refreshInterval = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadSites();
    loadStats();
    
    // Автообновление каждые 30 секунд
    refreshInterval = setInterval(() => {
        loadSites();
        loadStats();
    }, 30000);
});

// Загрузить список сайтов
async function loadSites() {
    try {
        const response = await fetch('/api/sites');
        sites = await response.json();
        renderSites();
    } catch (error) {
        console.error('Ошибка загрузки сайтов:', error);
        document.getElementById('sites-list').innerHTML = 
            '<div class="loading">Ошибка загрузки данных</div>';
    }
}

// Загрузить статистику
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('total-sites').textContent = stats.total_sites;
        document.getElementById('up-sites').textContent = stats.up_sites;
        document.getElementById('down-sites').textContent = stats.down_sites;
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Отобразить список сайтов
function renderSites() {
    const container = document.getElementById('sites-list');
    
    if (sites.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>Нет сайтов для мониторинга</h3>
                <p>Добавьте первый сайт, чтобы начать мониторинг</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = sites.map(site => {
        const statusClass = site.is_up === true ? 'up' : 
                           site.is_up === false ? 'down' : 'unknown';
        const statusText = site.is_up === true ? 'Доступен' : 
                          site.is_up === false ? 'Недоступен' : 'Не проверен';
        const lastCheck = site.last_check ? 
            new Date(site.last_check).toLocaleString('ru-RU') : 'Никогда';
        
        return `
            <div class="site-card">
                <div class="site-info">
                    <div class="site-name">${escapeHtml(site.name || site.url)}</div>
                    <div class="site-url">${escapeHtml(site.url)}</div>
                </div>
                <div class="site-status">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                    <span class="last-check">Проверено: ${lastCheck}</span>
                </div>
                <div class="site-actions">
                    <button class="btn btn-secondary btn-small" onclick="checkSiteNow(${site.id})">
                        Проверить
                    </button>
                    <button class="btn btn-danger btn-small" onclick="deleteSite(${site.id})">
                        Удалить
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Добавить сайт
async function addSite(event) {
    event.preventDefault();
    
    const url = document.getElementById('site-url').value.trim();
    const name = document.getElementById('site-name').value.trim();
    
    if (!url) {
        alert('Введите URL сайта');
        return;
    }
    
    try {
        const response = await fetch('/api/sites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url, name })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            closeAddSiteModal();
            document.getElementById('add-site-form').reset();
            loadSites();
            loadStats();
        } else {
            alert(data.error || 'Ошибка при добавлении сайта');
        }
    } catch (error) {
        console.error('Ошибка добавления сайта:', error);
        alert('Ошибка при добавлении сайта');
    }
}

// Удалить сайт
async function deleteSite(siteId) {
    if (!confirm('Вы уверены, что хотите удалить этот сайт из мониторинга?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/sites/${siteId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadSites();
            loadStats();
        } else {
            alert('Ошибка при удалении сайта');
        }
    } catch (error) {
        console.error('Ошибка удаления сайта:', error);
        alert('Ошибка при удалении сайта');
    }
}

// Проверить сайт немедленно
async function checkSiteNow(siteId) {
    try {
        const response = await fetch(`/api/sites/${siteId}/check`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadSites();
            loadStats();
        } else {
            alert('Ошибка при проверке сайта');
        }
    } catch (error) {
        console.error('Ошибка проверки сайта:', error);
        alert('Ошибка при проверке сайта');
    }
}

// Обновить список сайтов
function refreshSites() {
    loadSites();
    loadStats();
}

// Модальное окно добавления сайта
function showAddSiteModal() {
    document.getElementById('add-site-modal').style.display = 'block';
}

function closeAddSiteModal() {
    document.getElementById('add-site-modal').style.display = 'none';
}

// Закрыть модальное окно при клике вне его
window.onclick = function(event) {
    const modal = document.getElementById('add-site-modal');
    if (event.target == modal) {
        closeAddSiteModal();
    }
}

// Экранирование HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
