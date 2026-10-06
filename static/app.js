const API = '';
const genres = ['All', 'Action', 'Adventure', 'Animation', 'Comedy', 'Drama', 'Horror', 'Music', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller'];
const colors = {
  'Sci-Fi': 'linear-gradient(145deg,#33c4ff,#6a58ff 54%,#27184e)',
  Drama: 'linear-gradient(145deg,#ffbd59,#f46f74 54%,#532650)',
  Adventure: 'linear-gradient(145deg,#70e2bd,#1ca88e 54%,#173d54)',
  Mystery: 'linear-gradient(145deg,#c59bff,#7654d9 54%,#25234f)',
  Comedy: 'linear-gradient(145deg,#ffe168,#ff8c5b 54%,#9b3f72)',
  Romance: 'linear-gradient(145deg,#ff9acb,#fb5b94 54%,#763b83)',
  Crime: 'linear-gradient(145deg,#ffac72,#e45d52 54%,#39274d)',
  Music: 'linear-gradient(145deg,#ffdf73,#ff8e55 46%,#8a4fb4)',
  Animation: 'linear-gradient(145deg,#8cf2d0,#5bc8ff 54%,#5654ca)',
  Action: 'linear-gradient(145deg,#ffc26a,#fb594e 50%,#521b55)',
  Family: 'linear-gradient(145deg,#c4f47a,#43c9a6 54%,#2779a8)',
  Horror: 'linear-gradient(145deg,#ad91ff,#6553a8 54%,#1c2343)',
  Thriller: 'linear-gradient(145deg,#81b4ff,#4c5ca9 54%,#262447)',
  Fantasy: 'linear-gradient(145deg,#a88aff,#f078bd 54%,#3e2b75)',
  History: 'linear-gradient(145deg,#e1ba7b,#a76356 54%,#49324c)',
  Biography: 'linear-gradient(145deg,#b6d99b,#548975 54%,#273d52)',
};

let catalog = [];
let selected = new Set();
let watchlisted = new Set();
let activeGenre = 'All';
let query = '';
let exploreGenre = 'All';
let exploreQuery = '';
let exploreSort = 'rating';
let userId = '';
const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function movieCard(movie, { recommended = false, watchlist = false } = {}) {
  const liked = selected.has(movie.id);
  const saved = watchlisted.has(movie.id);
  const title = escapeHtml(movie.title);
  const genresLabel = movie.genres.map(escapeHtml).join(' · ').toUpperCase();
  const tone = colors[movie.genres[0]] || colors.Drama;
  const topRight = recommended
    ? `<span class="match">${movie.match}% MATCH</span>`
    : watchlist ? '<span class="collection-label">SAVED FOR LATER</span>' : '✳';
  const favoriteButton = !recommended && !watchlist
    ? `<button type="button" class="select-mark" data-action="toggle-like" aria-label="${liked ? 'Remove' : 'Add'} ${title} ${liked ? 'from' : 'to'} favorites" aria-pressed="${liked}">${liked ? '✓' : '+'}</button>`
    : '';
  let actions = '';
  if (recommended) {
    actions = `<div class="rec-actions"><button type="button" class="save-action ${saved ? 'saved' : ''}" data-action="toggle-watchlist" ${saved ? 'disabled' : ''}>${saved ? '✓ Saved' : '＋ Watchlist'}</button><button type="button" class="pass-action" data-action="dismiss" aria-label="Not for me">×</button></div>`;
  } else if (watchlist) {
    actions = '<div class="rec-actions"><button type="button" class="save-action remove-action" data-action="toggle-watchlist">Remove from my list</button></div>';
  }

  return `<article class="movie-card ${liked ? 'selected' : ''}" data-movie-id="${movie.id}">
    <div class="poster-art" style="background:${tone}" aria-hidden="true">
      <span class="art-top"><span>${movie.year}</span>${topRight}</span>
      <b>${title.toUpperCase()}</b><small>${genresLabel}</small>${favoriteButton}
    </div>
    <div class="movie-info"><div class="movie-title-row"><div class="movie-title">${title}</div><button type="button" class="detail-action" data-action="details">Details <span>↗</span></button></div>
      <div class="movie-meta"><span>${movie.year} · ${movie.runtime} min</span><span class="rating">★ ${movie.rating}</span></div>
    </div>${actions}
  </article>`;
}

function renderGenres() {
  const options = ['All', ...new Set([...genres.slice(1), ...catalog.flatMap((movie) => movie.genres)])].sort((a, b) => a === 'All' ? -1 : b === 'All' ? 1 : a.localeCompare(b));
  $('#genres').innerHTML = options.map((genre) => `<button class="genre-pill ${activeGenre === genre ? 'active' : ''}" data-genre="${escapeHtml(genre)}" aria-pressed="${activeGenre === genre}">${escapeHtml(genre)}</button>`).join('');
}

function renderExploreGenres() {
  const options = ['All', ...new Set(catalog.flatMap((movie) => movie.genres))].sort((a, b) => a === 'All' ? -1 : b === 'All' ? 1 : a.localeCompare(b));
  $('#explore-genres').innerHTML = options.map((genre) => `<button class="genre-pill ${exploreGenre === genre ? 'active' : ''}" data-explore-genre="${escapeHtml(genre)}" aria-pressed="${exploreGenre === genre}">${escapeHtml(genre)}</button>`).join('');
}

function renderExplore() {
  let rows = catalog.filter((movie) => {
    const matchesGenre = exploreGenre === 'All' || movie.genres.includes(exploreGenre);
    const searchable = `${movie.title} ${movie.overview} ${movie.genres.join(' ')} ${movie.keywords.join(' ')}`.toLowerCase();
    return matchesGenre && (!exploreQuery || searchable.includes(exploreQuery));
  });
  rows = [...rows].sort((a, b) => {
    if (exploreSort === 'newest') return b.year - a.year || b.rating - a.rating;
    if (exploreSort === 'title') return a.title.localeCompare(b.title);
    if (exploreSort === 'runtime') return a.runtime - b.runtime || b.rating - a.rating;
    return b.rating - a.rating || b.year - a.year;
  });
  $('#explore-grid').innerHTML = rows.map((movie) => movieCard(movie)).join('') || '<div class="empty">No movies match those filters. Try a different genre or search.</div>';
  $('#explore-count').textContent = `${rows.length} ${rows.length === 1 ? 'film' : 'films'}`;
  $('#explore-caption').textContent = rows.length === catalog.length ? `All ${catalog.length} stories in the ReelRank library` : `${rows.length} of ${catalog.length} films match your search`;
}

function updatePickNote() {
  const count = selected.size;
  $('#pick-note').textContent = count === 0 ? 'Pick a few to tune your mix' : count === 1 ? 'One favorite is shaping your picks' : `${count} favorites are shaping your picks`;
}

function renderCatalog() {
  const rows = catalog.filter((movie) => (activeGenre === 'All' || movie.genres.includes(activeGenre)) && (!query || movie.title.toLowerCase().includes(query) || movie.overview.toLowerCase().includes(query)));
  $('#taste-grid').innerHTML = rows.map((movie) => movieCard(movie)).join('') || '<div class="empty">No titles found. Try another search.</div>';
  $('#pick-count').textContent = `${selected.size} picked`;
  updatePickNote();
}

async function renderRecommendations() {
  try {
    const response = await fetch(`${API}/api/users/${userId}/recommendations?limit=10`);
    if (!response.ok) throw new Error('Recommendation request failed');
    const rows = await response.json();
    $('#recommendations').innerHTML = rows.map((movie) => movieCard(movie, { recommended: true })).join('') || '<div class="empty">No matches for that mood yet. Add a few favorites to tune your picks.</div>';
    $('#recommendation-caption').innerHTML = `<span class="api-led"></span> ${rows.length} picks · ranked by ${escapeHtml(window.reelrankModel || 'your taste profile')}`;
  } catch {
    $('#recommendations').innerHTML = '<div class="empty">Could not connect to the recommendation service. Refresh to try again.</div>';
    $('#recommendation-caption').textContent = 'Recommendation service unavailable';
  }
}

async function renderWatchlist() {
  try {
    const response = await fetch(`${API}/api/users/${userId}/watchlist`);
    if (!response.ok) throw new Error('Watchlist request failed');
    const rows = await response.json();
    watchlisted = new Set(rows.map((movie) => movie.id));
    $('#watchlist-grid').innerHTML = rows.map((movie) => movieCard(movie, { watchlist: true })).join('') || '<div class="empty watch-empty"><span class="empty-icon">✦</span><strong>Your next movie night starts here.</strong><span>Save a recommendation and it will appear in your list.</span><a class="primary-btn small-btn" href="#discover">Find a movie</a></div>';
    const label = `${rows.length} saved`;
    $('#watch-count').textContent = label;
    $('#nav-watch-count').textContent = rows.length;
  } catch {
    $('#watchlist-grid').innerHTML = '<div class="empty">Could not load your watchlist. Check the API connection and refresh.</div>';
  }
}

function showMovieDetails(id) {
  const movie = catalog.find((item) => item.id === id);
  if (!movie) return;
  const dialog = $('#movie-dialog');
  const tone = colors[movie.genres[0]] || colors.Drama;
  const title = escapeHtml(movie.title);
  const liked = selected.has(id);
  const saved = watchlisted.has(id);
  $('#movie-detail').innerHTML = `<div class="detail-layout" data-movie-id="${id}">
    <div class="detail-poster" style="background:${tone}"><span>${movie.year} · ${movie.runtime} MIN</span><b>${title.toUpperCase()}</b><small>★ ${movie.rating} AUDIENCE SCORE</small></div>
    <div class="detail-copy"><div class="eyebrow">A REELRANK PICK</div><h2 id="detail-title">${title}</h2>
      <div class="detail-genres">${movie.genres.map((genre) => `<span>${escapeHtml(genre)}</span>`).join('')}</div>
      <p class="detail-overview">${escapeHtml(movie.overview)}</p>
      <div class="keyword-row"><span>THEMES</span>${movie.keywords.map((word) => `<i>${escapeHtml(word)}</i>`).join('')}</div>
      <div class="detail-actions"><button class="detail-primary" type="button" data-action="toggle-watchlist">${saved ? '✓ In your watchlist' : '＋ Add to watchlist'}</button><button class="detail-secondary" type="button" data-action="toggle-like">${liked ? '♥ In your favorites' : '♡ I like this'}</button></div>
    </div></div>`;
  if (!dialog.open) dialog.showModal();
}

function toast(message) {
  const element = $('#toast');
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove('show'), 2100);
}

async function sendFeedback(movieId, action) {
  try {
    const response = await fetch(`${API}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ movie_id: movieId, action }),
    });
    if (!response.ok) throw new Error('Feedback was not saved');
    if (action === 'watchlist') toast('Saved for your next movie night ✦');
    if (action === 'unwatchlist') toast('Removed from your list');
    return true;
  } catch {
    toast('Could not save that change. Please try again.');
    return false;
  }
}

async function handleAction(action, movieId) {
  if (action === 'details') {
    showMovieDetails(movieId);
    return;
  }
  if (action === 'toggle-like') {
    const nextAction = selected.has(movieId) ? 'unlike' : 'like';
    if (!await sendFeedback(movieId, nextAction)) return;
    nextAction === 'like' ? selected.add(movieId) : selected.delete(movieId);
    renderCatalog();
    renderExplore();
    await renderRecommendations();
  } else if (action === 'toggle-watchlist') {
    const nextAction = watchlisted.has(movieId) ? 'unwatchlist' : 'watchlist';
    if (!await sendFeedback(movieId, nextAction)) return;
    nextAction === 'watchlist' ? watchlisted.add(movieId) : watchlisted.delete(movieId);
    await Promise.all([renderWatchlist(), renderRecommendations()]);
  } else if (action === 'dismiss') {
    if (!await sendFeedback(movieId, 'dislike')) return;
    await renderRecommendations();
  }
  if ($('#movie-dialog').open) showMovieDetails(movieId);
}

function bindActions(container) {
  container.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const movieId = Number(button.closest('[data-movie-id]')?.dataset.movieId);
    if (movieId) void handleAction(button.dataset.action, movieId);
  });
}

async function checkHealth() {
  const status = $('#api-status');
  try {
    const response = await fetch(`${API}/health`);
    if (!response.ok) throw new Error('API offline');
    const data = await response.json();
    window.reelrankModel = data.model || 'content model';
    status.dataset.state = 'online';
    status.querySelector('.status-label').textContent = 'API ONLINE';
    status.title = `${window.reelrankModel} · ${data.catalog_size} movies`;
    $('#recommendation-caption').innerHTML = `<span class="api-led"></span> Live from ${escapeHtml(window.reelrankModel)}`;
    return data;
  } catch {
    status.dataset.state = 'offline';
    status.querySelector('.status-label').textContent = 'API OFFLINE';
    status.title = 'Could not reach the recommendation service';
    $('#recommendation-caption').textContent = 'Reconnect the API to refresh your picks';
    return null;
  }
}

async function init() {
  renderGenres();
  try {
    const accountResponse = await fetch(`${API}/api/auth/me`);
    if (accountResponse.status === 401) {
      window.location.replace('/login');
      return;
    }
    if (!accountResponse.ok) throw new Error('Could not load your account');
    const account = await accountResponse.json();
    userId = account.id;
    $('#avatar-initial').textContent = account.display_name.trim().charAt(0).toUpperCase() || 'R';
    $('#avatar-initial').title = account.display_name;
    const health = await checkHealth();
    const [movieResponse, preferenceResponse] = await Promise.all([
      fetch(`${API}/api/movies`),
      fetch(`${API}/api/users/${userId}/preferences`),
    ]);
    if (!movieResponse.ok || !preferenceResponse.ok) throw new Error('Could not load the app data');
    catalog = await movieResponse.json();
    const preferences = await preferenceResponse.json();
    selected = new Set(preferences.liked);
    watchlisted = new Set(preferences.watchlist);
    renderGenres();
    renderCatalog();
    renderExploreGenres();
    renderExplore();
    await Promise.all([renderRecommendations(), renderWatchlist()]);
  } catch {
    $('#taste-grid').innerHTML = '<div class="empty">Could not load ReelRank. Check the API connection and refresh the page.</div>';
  }
}

bindActions($('#taste-grid'));
bindActions($('#recommendations'));
bindActions($('#explore-grid'));
bindActions($('#watchlist-grid'));
bindActions($('#movie-detail'));
$('#genres').addEventListener('click', (event) => {
  const button = event.target.closest('[data-genre]');
  if (button) {
    activeGenre = button.dataset.genre;
    renderGenres();
    renderCatalog();
  }
});
$('#search').addEventListener('input', (event) => {
  query = event.target.value.trim().toLowerCase();
  renderCatalog();
});
$('#explore-genres').addEventListener('click', (event) => {
  const button = event.target.closest('[data-explore-genre]');
  if (button) {
    exploreGenre = button.dataset.exploreGenre;
    renderExploreGenres();
    renderExplore();
  }
});
$('#explore-search').addEventListener('input', (event) => {
  exploreQuery = event.target.value.trim().toLowerCase();
  renderExplore();
});
$('#explore-sort').addEventListener('change', (event) => {
  exploreSort = event.target.value;
  renderExplore();
});
$('#refresh').addEventListener('click', renderRecommendations);
$('#logout-button').addEventListener('click', async () => {
  await fetch(`${API}/api/auth/logout`, { method: 'POST' });
  localStorage.removeItem('reelrank-user-id');
  window.location.replace('/login');
});
$('#dialog-close').addEventListener('click', () => $('#movie-dialog').close());
$('#movie-dialog').addEventListener('click', (event) => {
  if (event.target === $('#movie-dialog')) $('#movie-dialog').close();
});
setInterval(checkHealth, 45000);
init();
