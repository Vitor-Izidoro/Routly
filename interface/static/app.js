/* Painel sem dependências externas. Conteúdo de logs e arquivos nunca vira HTML cru. */
const $ = (selector, root = document) => root.querySelector(selector);
const icons = {
  check: '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="m7 12 3 3 7-7"/>',
  leaf: '<path d="M20 4C9 2 2 7 5 15s16 5 15-11Z"/><path d="M4 21 15 10M10 15v-5m0 5h5"/>',
  chart: '<path d="M4 3v17h17M8 15v-4m5 4V7m5 8V4"/>',
  route: '<circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 5h8a4 4 0 0 1 0 8H9a3 3 0 0 0 0 6h8"/>',
  map: '<path d="m3 5 6-2 6 3 6-2v15l-6 2-6-3-6 2Zm6-2v15m6-12v15"/>',
  folder: '<path d="M3 7V5a2 2 0 0 1 2-2h5l3 4h6a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
  activity: '<path d="M2 12h4l3-8 6 16 3-8h4"/>',
  play: '<path d="m8 4 12 8-12 8Z"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  file: '<path d="M14 2H5v20h14V7Zm0 0v6h5M8 12h8m-8 4h8"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.file}</svg>`;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusNames = {fila:'Na fila', executando:'Executando', concluido:'Concluído', falhou:'Falhou', cancelado:'Cancelado', interrompido:'Interrompido'};
const badge = status => `<span class="badge ${escape(status)}">${escape(statusNames[status] || status)}</span>`;
const state = {catalogo:null, grupo:'testes', jobs:[], selected:null, detail:null, tab:'results', library:[], config:[], autoScroll:true, polling:false, preview:0};
let selectionVersion = 0, previewController = null;
function invalidatePreview() {
  state.preview++;
  previewController?.abort();
  previewController = null;
}
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const motions = new WeakMap(), activeMotions = new Set(), closingDialogs = new WeakMap();
const easeOut = 'cubic-bezier(.22, 1, .36, 1)';
function animate(node, frames, options={}) {
  if (!node) return Promise.resolve();
  motions.get(node)?.cancel();
  if (reducedMotion.matches || !node.animate) return Promise.resolve();
  const animation = node.animate(frames, {duration:320, easing:easeOut, ...options});
  motions.set(node, animation); activeMotions.add(animation);
  return animation.finished.catch(() => {}).finally(() => {
    activeMotions.delete(animation);
    if (motions.get(node) === animation) motions.delete(node);
  });
}
function reveal(node, delay=0) {
  return animate(node, [{opacity:0, transform:'translateY(10px)'}, {opacity:1, transform:'translateY(0)'}], {delay, fill:'backwards'});
}
function scrollToSection(selector) {
  $(selector).scrollIntoView({behavior:reducedMotion.matches ? 'instant' : 'smooth', block:'start'});
}
function scrollTerminal(node) {
  node.scrollTo({top:node.scrollHeight, behavior:reducedMotion.matches ? 'instant' : 'smooth'});
}
function updateText(node, value) {
  if (node.textContent === String(value)) return;
  node.textContent = value;
  animate(node, [{opacity:.4, transform:'translateY(3px)'}, {opacity:1, transform:'translateY(0)'}], {duration:220});
}
function openDialog(dialog) {
  closingDialogs.delete(dialog); dialog.classList.remove('is-closing');
  if (!dialog.open) dialog.showModal();
  animate(dialog, [{opacity:0, transform:'translateY(14px) scale(.98)'}, {opacity:1, transform:'translateY(0) scale(1)'}]);
}
async function closeDialog(dialog) {
  if (!dialog.open || closingDialogs.has(dialog)) return;
  if (dialog.id === 'preview-dialog') invalidatePreview();
  const token = {}; closingDialogs.set(dialog, token); dialog.classList.add('is-closing');
  await animate(dialog, [{opacity:1, transform:'translateY(0) scale(1)'}, {opacity:0, transform:'translateY(8px) scale(.985)'}], {duration:160});
  if (closingDialogs.get(dialog) !== token) return;
  closingDialogs.delete(dialog);
  // Limpa a sessão encerrada antes de fechar. O evento nativo `close` é
  // assíncrono e pode chegar depois que outro arquivo já tiver sido aberto.
  if (dialog.id === 'preview-dialog') $('#preview-body').replaceChildren();
  dialog.close(); dialog.classList.remove('is-closing');
  observeArrivals();
}
const arrivals = new IntersectionObserver(entries => {
  entries.forEach(({target, isIntersecting}) => {
    if (!isIntersecting || document.querySelector('dialog[open]')) return;
    arrivals.unobserve(target); delete target.dataset.arrival;
    animate(target, [{opacity:0, transform:'translateX(-16px) scale(.97)', backgroundColor:'#dceccf'}, {opacity:1, transform:'translateX(0) scale(1)', backgroundColor:getComputedStyle(target).backgroundColor}], {duration:480});
  });
}, {threshold:.15});
function observeArrivals() {
  if (document.querySelector('dialog[open]')) return;
  document.querySelectorAll('[data-arrival]').forEach(node => { arrivals.unobserve(node); arrivals.observe(node); });
}
reducedMotion.addEventListener('change', () => {
  if (reducedMotion.matches) activeMotions.forEach(animation => animation.cancel());
});
let toastTimer;
let toastVersion = 0;
function toast(message, error=false) {
  const version = ++toastVersion;
  const node = $('#toast'); node.textContent = message; node.hidden = false; node.classList.toggle('error', error);
  reveal(node);
  clearTimeout(toastTimer); toastTimer = setTimeout(async () => {
    await animate(node, [{opacity:1, transform:'translateY(0)'}, {opacity:0, transform:'translateY(8px)'}], {duration:180});
    if (version === toastVersion) node.hidden = true;
  }, error ? 8000 : 4000);
}
async function api(url, body) {
  const response = await fetch(url, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await response.json(); if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir a solicitação.'); return data;
}
function grupo(id) { return state.catalogo.grupos.find(g => g.id === id); }
function operacao(id) { return state.catalogo.operacoes.find(o => o.id === id); }
function hydrateIcons(root=document) { root.querySelectorAll('[data-icon]').forEach(n => n.innerHTML = icon(n.dataset.icon)); }
function dataHora(value) { return new Date(value).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}); }
function duration(job) {
  if (!job.inicio) return 'Aguardando a fila';
  const seconds = Math.max(0, Math.floor(((job.fim ? new Date(job.fim) : Date.now()) - new Date(job.inicio)) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds/60)}min ${seconds%60}s`;
}
function renderNavigation() {
  if (!$('#navigation').children.length) {
    $('#navigation').innerHTML = state.catalogo.grupos.map(g => `<button class="nav-button" data-group="${g.id}">${icon(g.icone)}${escape(g.nome)}</button>`).join('');
    $('#navigation').querySelectorAll('button').forEach(b => b.onclick = () => selectGroup(b.dataset.group));
  }
  $('#navigation').querySelectorAll('button').forEach(button => {
    const selected = button.dataset.group === state.grupo;
    button.classList.toggle('active', selected);
    if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
}
function selectGroup(id) {
  if (state.grupo === id) return;
  state.grupo = id; $('#search').value = ''; renderNavigation(); renderCards();
  reveal($('#experiments .section-heading'));
  if (window.innerWidth < 700) scrollToSection('#experiments');
}
function disponibilidade(op) {
  const env = state.catalogo.ambiente;
  if (op.grafo && !env.grafo) return 'Grafo ausente';
  if (op.shapefiles && (!env.ruas || (op.id === 'etl' && !env.curvas))) return 'Shapefile ausente';
  return 'Pronto para executar';
}
function renderCards() {
  const g = grupo(state.grupo), query = $('#search').value.toLocaleLowerCase('pt-BR');
  const ops = state.catalogo.operacoes.filter(o => o.grupo === g.id && `${o.nome} ${o.descricao}`.toLocaleLowerCase('pt-BR').includes(query));
  $('#group-title').textContent = g.nome; $('#group-description').textContent = g.descricao;
  $('#group-overline').textContent = `0${state.catalogo.grupos.indexOf(g)+1} / EXPLORAR E VALIDAR`;
  $('#visible-count').textContent = `${ops.length} operações`;
  $('#cards').innerHTML = ops.map(o => `<article class="test-card"><div class="card-top"><span class="card-icon">${icon(g.icone)}</span><span class="card-tag">${g.id === 'testes' ? 'AUTOMATIZADO' : o.id === 'pipeline' ? 'PIPELINE' : 'EXPERIMENTO'}</span></div><h3>${escape(o.nome)}</h3><p>${escape(o.descricao)}</p><div class="card-footer"><span class="card-status"><span class="live-dot"></span>${disponibilidade(o)}</span><button class="card-run" data-run="${o.id}" aria-label="${o.campos.length ? 'Configurar' : 'Executar'} ${escape(o.nome)}">${icon('play')}${o.campos.length ? 'Configurar' : 'Executar'}</button></div></article>`).join('') || '<p class="empty">Nenhuma operação encontrada neste grupo.</p>';
  $('#cards').querySelectorAll('[data-run]').forEach(b => b.onclick = () => configure([operacao(b.dataset.run)]));
  $('#cards').querySelectorAll('.test-card').forEach((card, i) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'card-explanation';
    button.innerHTML = `${icon('file')}<span>O que este teste comprova?</span><span aria-hidden="true">↗</span>`;
    button.setAttribute('aria-label', `O que este teste comprova? ${ops[i].nome}`);
    button.setAttribute('aria-haspopup', 'dialog');
    button.onclick = () => explain(ops[i]);
    card.insertBefore(button, $('.card-footer', card));
  });
  $('#cards').querySelectorAll('.test-card').forEach((card, i) => reveal(card, Math.min(i, 7)*28));
}
function explain(op) {
  const headings = ['O que verifica ou demonstra', 'Como funciona', 'Como interpretar o resultado', 'Limites da conclusão'];
  $('#explanation-title').textContent = op.nome;
  $('#explanation-group').textContent = grupo(op.grupo).nome;
  $('#explanation-body').innerHTML = explicacaoDaOperacao(op).map((text, i) => `<section class="explanation-section"><h3>${headings[i]}</h3><p>${escape(text)}</p></section>`).join('');
  const dialog = $('#explanation-dialog');
  openDialog(dialog); dialog.scrollTop = 0;
  $('#explanation-title').focus({preventScroll:true});
}
function configure(ops) {
  state.config = ops;
  $('#config-title').textContent = ops.length === 1 ? ops[0].nome : `Executar grupo · ${grupo(ops[0].grupo).nome}`;
  $('#config-description').textContent = ops.length === 1 ? ops[0].descricao : `${ops.length} operações serão executadas em sequência: ${ops.map(o => o.nome).join(', ')}. Os parâmetros abaixo são compartilhados pelas operações que os utilizam.`;
  const fields = new Map(ops.flatMap(o => o.campos).map(c => [c.id, c]));
  $('#config-fields').innerHTML = [...fields.values()].map(c => {
    const id = 'field-' + c.id;
    if (c.tipo === 'checkbox') return `<label class="form-field checkbox" data-field="${c.id}"><input id="${id}" name="${c.id}" type="checkbox" ${c.padrao ? 'checked' : ''}>${escape(c.nome)}</label>`;
    const input = c.tipo === 'select' ? `<select id="${id}" name="${c.id}">${c.opcoes.map(v => `<option ${v === c.padrao ? 'selected' : ''} value="${escape(v)}">${escape(v)}</option>`).join('')}</select>` : `<input id="${id}" name="${c.id}" type="${c.tipo === 'number' ? 'number' : 'text'}" value="${escape(c.padrao)}" ${c.min !== undefined ? `min="${c.min}"` : ''} step="${c.inteiro ? '1' : 'any'}" ${!c.vazio ? 'required' : ''} ${c.tipo === 'text' ? 'maxlength="250"' : ''}>`;
    return `<label class="form-field ${c.tipo === 'text' || c.tipo === 'numbers' ? 'full' : ''}" data-field="${c.id}">${escape(c.nome)}${input}</label>`;
  }).join('') || '<p class="small muted">Esta operação usa a configuração padrão do projeto. O resultado será salvo no histórico.</p>';
  function dependencies() {
    for (const c of fields.values()) {
      const label = $(`[data-field="${c.id}"]`);
      const hidden = c.quando && !Object.entries(c.quando).every(([key,value]) => $(`[name="${key}"]`, $('#config-form'))?.value === value);
      const wasHidden = label.hidden;
      label.hidden = !!hidden;
      $('input,select', label).disabled = !!hidden;
      if (wasHidden && !hidden) reveal(label);
    }
  }
  $('#config-fields').onchange = dependencies; dependencies();
  const missing = [...new Set(ops.map(disponibilidade).filter(s => s !== 'Pronto para executar'))];
  const notes = [...missing];
  if (ops.some(o => ['pareto','boa','pipeline','mapa'].includes(o.id))) notes.push('O cálculo de Pareto pode demorar, conforme a origem e o destino. Você pode cancelar a execução no histórico.');
  if (ops.some(o => o.id === 'pipeline')) notes.push('O pipeline mantém os padrões do terminal: eficácia com 100 pares, HDDT1 carregado e 21 passos de α. O número de pares deste formulário controla o Monte Carlo.');
  $('#config-notice').hidden = !notes.length; $('#config-notice').textContent = notes.join(' · ');
  openDialog($('#config-dialog'));
}
async function startJobs(ops, values={}) {
  const jobs = await api('/api/execucoes', {execucoes:ops.map(o => ({operacao:o.id, parametros:Object.fromEntries(o.campos.map(c => [c.id, values[c.id] ?? c.padrao]))}))});
  state.jobs = [...jobs, ...state.jobs];
  await selectJob(jobs[0].id);
  toast(jobs.length === 1 ? 'Execução adicionada à fila.' : `${jobs.length} execuções adicionadas à fila.`);
}
$('#config-form').onsubmit = async event => {
  event.preventDefault(); const values = {};
  for (const input of $('#config-fields').querySelectorAll('input,select')) if (!input.disabled) values[input.name] = input.type === 'checkbox' ? input.checked : input.value;
  const button = $('button[type="submit"]', event.target), original = button.innerHTML;
  button.disabled = true; button.classList.add('is-loading'); button.setAttribute('aria-busy','true'); button.textContent = 'Adicionando à fila…';
  try {
    await startJobs(state.config, values);
    await closeDialog($('#config-dialog'));
    $('#history-list').scrollTo({top:0,left:0,behavior:'instant'});
    scrollToSection('#results-section'); observeArrivals();
  } catch (e) { toast(e.message, true); } finally {
    button.disabled = false; button.classList.remove('is-loading'); button.removeAttribute('aria-busy'); button.innerHTML = original;
  }
};
function renderHistory() {
  updateText($('#history-count'), state.jobs.length);
  const list = $('#history-list'), initialized = !!list.dataset.key;
  const key = JSON.stringify([state.jobs.map(j => [j.id,j.status]),state.selected]);
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  const existing = new Map([...list.querySelectorAll('[data-job]')].map(node => [node.dataset.job, node]));
  const positions = new Map([...existing].map(([id,node]) => [id,node.getBoundingClientRect()]));
  existing.forEach(node => motions.get(node)?.cancel());
  list.querySelector('.empty')?.remove();
  const jobs = state.jobs.slice(0,100), ids = new Set(jobs.map(j=>j.id));
  existing.forEach((node,id) => { if (!ids.has(id)) { arrivals.unobserve(node); node.remove(); } });
  jobs.forEach((job,index) => {
    let button = existing.get(job.id);
    if (!button) {
      button = document.createElement('button'); button.className='history-item'; button.dataset.job=job.id;
      button.innerHTML=`<strong>${escape(job.nome)}</strong><span class="history-meta">${badge(job.status)}<span>${dataHora(job.criado)}</span></span>`;
      if (initialized) button.dataset.arrival='true';
      button.onclick=()=>selectJob(job.id);
    }
    if (list.children[index] !== button) list.insertBefore(button, list.children[index] || null);
    button.classList.toggle('active',state.selected===job.id);
    if(state.selected===job.id)button.setAttribute('aria-current','true');else button.removeAttribute('aria-current');
    const status=$('.badge',button);
    if(button.dataset.status && button.dataset.status!==job.status){
      status.className='badge '+job.status; status.textContent=statusNames[job.status];
      animate(status,[{opacity:.35,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],{duration:300});
    }
    button.dataset.status=job.status;
  });
  jobs.forEach(job=>{
    const node=list.querySelector(`[data-job="${job.id}"]`), before=positions.get(job.id);
    if(!before)return;
    const after=node.getBoundingClientRect(), x=before.left-after.left, y=before.top-after.top;
    if(x||y)animate(node,[{transform:`translate(${x}px,${y}px)`},{transform:'translate(0,0)'}],{duration:400});
  });
  if(!jobs.length)list.innerHTML='<div class="empty small">As execuções aparecerão aqui.</div>';
  observeArrivals();
}
async function selectJob(id) {
  if (state.selected === id && state.detail?.id === id) return;
  const version = ++selectionVersion;
  state.selected = id; state.detail = null;
  state.tab = ['fila','executando'].includes(state.jobs.find(j=>j.id===id)?.status) ? 'log' : 'results';
  renderHistory(); renderResult();
  try {
    // A seleção não depende do polling: um refresh em andamento não pode
    // descartar este pedido nem deixar cartões de outra execução clicáveis.
    const detail = await api('/api/execucoes/'+id);
    if (version !== selectionVersion || state.selected !== id) return;
    state.detail = detail; renderResult();
  } catch(e) {
    if (version !== selectionVersion || state.selected !== id) return;
    $('#result-content').removeAttribute('aria-busy');
    $('#result-content').innerHTML='<div class="empty"><p>Não foi possível carregar esta execução.</p><button class="button secondary" id="retry-result">Tentar novamente</button></div>';
    $('#retry-result').onclick=()=>selectJob(id);
    toast(e.message,true);
  }
}
function renderResult() {
  const library = state.selected === 'biblioteca', job = state.detail;
  if (state.selected && !library && (!job || job.id !== state.selected)) {
    const content = $('#result-content'), loadingKey = 'loading:'+state.selected;
    if (content.dataset.key !== loadingKey) {
      motions.get(content)?.cancel();
      content.dataset.key=loadingKey;
      content.setAttribute('aria-busy','true');
      $('#result-header').dataset.key=loadingKey;
      $('#result-header').innerHTML=`<div><h3>${escape(state.jobs.find(j=>j.id===state.selected)?.nome || 'Execução')}</h3><p class="small muted">Carregando resultados…</p></div>`;
      content.innerHTML='<div class="empty"><p>Carregando os arquivos desta execução…</p></div>';
      $('#artifact-count').textContent='0';
      document.querySelectorAll('.result-tabs button').forEach(button=>button.disabled=true);
    }
    return;
  }
  $('#result-content').removeAttribute('aria-busy');
  const files = library ? state.library : job?.artefatos || [];
  updateText($('#artifact-count'), files.length);
  const header = $('#result-header'), headerKey = JSON.stringify([state.selected,job?.status]);
  const headerChanged = header.dataset.key !== headerKey;
  if (library && headerChanged) {
    $('#result-header').innerHTML = '<div><h3>Resultados salvos no projeto</h3><p class="small muted">Arquivos de referência em resultados_validacao/. Não representam uma execução nova.</p></div><span class="badge">Referência</span>';
  } else if (job && headerChanged) {
    const code = job.codigo == null ? '' : ` · código de saída ${job.codigo}`;
    $('#result-header').innerHTML = `<div><h3>${escape(job.nome)}</h3><p class="small muted">${dataHora(job.criado)} · ${duration(job)}${code}</p></div><div class="result-actions">${badge(job.status)}${['fila','executando'].includes(job.status) ? '<button class="cancel-button" id="cancel-job">Cancelar</button>' : '<button class="card-run" id="rerun-job">Repetir ↻</button>'}</div>`;
    if ($('#cancel-job')) $('#cancel-job').onclick = async () => { try { await api('/api/cancelar/'+job.id,{}); await refresh(); toast('Execução cancelada.'); } catch (e) {toast(e.message,true);} };
    if ($('#rerun-job')) $('#rerun-job').onclick = () => {
      const op = operacao(job.operacao);
      configure([{...op, campos:op.campos.map(c => ({...c,padrao:Array.isArray(job.parametros[c.id]) ? job.parametros[c.id].join(', ') : job.parametros[c.id] ?? c.padrao}))}]);
    };
  }
  if (job) {
    const code = job.codigo == null ? '' : ` · código de saída ${job.codigo}`;
    $('p', header).textContent = `${dataHora(job.criado)} · ${duration(job)}${code}`;
  }
  if ((job || library) && headerChanged) { header.dataset.key = headerKey; reveal(header); }
  for (const id of ['results','log','params']) {
    const tab = $('#tab-'+id); tab.classList.toggle('active', state.tab === id); tab.setAttribute('aria-selected', state.tab === id); tab.tabIndex = state.tab === id ? 0 : -1;
    tab.disabled = library && id !== 'results';
  }
  $('#result-content').setAttribute('aria-labelledby', 'tab-'+state.tab);
  const key = JSON.stringify([state.selected, state.tab, state.tab === 'results' ? files : null, state.tab === 'results' ? job?.status : null, state.tab === 'params' ? job?.parametros : null]);
  const content = $('#result-content');
  if (content.dataset.key === key) {
    if (state.tab === 'log' && $('#terminal')) {
      const terminal = $('#terminal');
      if (terminal.textContent !== (job?.log || 'Aguardando o início da execução…')) {
        terminal.textContent = job?.log || 'Aguardando o início da execução…';
        if (state.autoScroll) scrollTerminal(terminal);
      }
    }
    return;
  }
  const previousHeight = content.getBoundingClientRect().height;
  motions.get(content)?.cancel();
  const view = `${state.selected}:${state.tab}`, viewChanged = content.dataset.view !== view;
  content.dataset.view = view;
  content.dataset.key = key;
  if (!job && !library) return;
  if (state.tab === 'log') {
    content.innerHTML = `<div class="log-toolbar"><label><input type="checkbox" id="auto-scroll" ${state.autoScroll ? 'checked' : ''}>Acompanhar novas linhas</label><a href="${job.log_url}" download="terminal-${job.id}.txt">Baixar log completo ↓</a></div><pre class="terminal" id="terminal"></pre>`;
    $('#terminal').textContent = job.log || 'Aguardando o início da execução…';
    $('#auto-scroll').onchange = event => state.autoScroll = event.target.checked;
    if (state.autoScroll) $('#terminal').scrollTop = $('#terminal').scrollHeight;
  } else if (state.tab === 'params') {
    const op = operacao(job.operacao);
    content.innerHTML = `<table class="params"><tbody>${Object.entries(job.parametros).map(([k,v]) => `<tr><td>${escape(op?.campos.find(c => c.id === k)?.nome || k)}</td><td>${escape(typeof v === 'boolean' ? v ? 'Sim' : 'Não' : Array.isArray(v) ? v.join(', ') : v)}</td></tr>`).join('') || '<tr><td>Configuração padrão</td><td>Sem parâmetros adicionais</td></tr>'}</tbody></table>`;
  } else {
    const sorted = [...files].sort((a,b) => Number(['png','jpg','jpeg'].includes(b.tipo)) - Number(['png','jpg','jpeg'].includes(a.tipo)));
    content.innerHTML = files.length ? `<p class="artifact-intro">${library ? 'Explore as evidências já disponíveis no repositório.' : 'Arquivos produzidos por esta execução. Clique para visualizar ou baixar.'}</p><div class="artifact-grid">${sorted.map((f,i) => `<button class="artifact" data-file="${i}">${['png','jpg','jpeg'].includes(f.tipo) ? `<img loading="lazy" src="${f.url}" alt="${escape(f.nome)}">` : `<span class="artifact-symbol">${icon(f.tipo === 'html' ? 'map' : 'file')}</span>`}<span class="artifact-label"><strong>${escape(f.nome)}</strong><small>${f.tipo.toUpperCase()} · ${Math.max(1,Math.round(f.tamanho/1024))} KB · VISUALIZAR ↗</small></span></button>`).join('')}</div>` : `<div class="empty"><span>${icon('chart')}</span><h3>${job?.status === 'falhou' ? 'A execução encontrou um erro.' : ['fila','executando'].includes(job?.status) ? 'Aguardando os resultados…' : 'Saída disponível no terminal.'}</h3><p>${job?.status === 'falhou' ? 'Consulte o terminal para ver a causa e as orientações.' : 'Esta execução ainda não produziu gráficos ou arquivos.'}</p><button class="button secondary" id="go-log">Ver saída do terminal →</button></div>`;
    content.querySelectorAll('[data-file]').forEach(b => b.onclick = () => preview(sorted[Number(b.dataset.file)]));
    if ($('#go-log')) $('#go-log').onclick = () => setTab('log');
  }
  if (viewChanged) {
    content.scrollTop=0;
    const height=content.getBoundingClientRect().height;
    animate(content,[{height:`${previousHeight}px`,opacity:.25,transform:'translateY(6px)'},{height:`${height}px`,opacity:1,transform:'translateY(0)'}]);
  } else reveal(content);
  content.querySelectorAll('.artifact').forEach((card,i)=>reveal(card,Math.min(i,7)*25));
}
function setTab(tab) { state.tab = tab; renderResult(); }
function markdown(text) {
  const inline = value => escape(value).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  const lines = text.split('\n'); let output = '', table = false, code = false;
  for (const line of lines) {
    if (line.startsWith('```')) { if(table){output+='</tbody></table>';table=false;} code=!code; output += code ? '<pre>' : '</pre>'; continue; }
    if (code) { output += escape(line)+'\n'; continue; }
    if (line.trim().startsWith('|')) {
      if (/^[| :\-]+$/.test(line.trim())) continue;
      if (!table) { output += '<table><tbody>'; table = true; }
      output += '<tr>'+line.trim().replace(/^\||\|$/g,'').split('|').map(cell=>'<td>'+inline(cell.trim())+'</td>').join('')+'</tr>'; continue;
    }
    if (table) {output+='</tbody></table>';table=false;}
    const heading = line.match(/^(#{1,3})\s+(.+)/);
    if (heading) output+=`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`;
    else if (line.trim()) output+='<p>'+inline(line)+'</p>';
  }
  return output+(table?'</tbody></table>':'')+(code?'</pre>':'');
}
async function preview(file) {
  invalidatePreview();
  const request = state.preview;
  const controller = new AbortController(); previewController = controller;
  $('#preview-title').textContent = file.nome;
  const download = $('#preview-download'); download.href = file.url; download.download = file.nome.split('/').at(-1);
  const body = $('#preview-body'); body.innerHTML = '<p class="empty">Carregando arquivo…</p>';
  openDialog($('#preview-dialog'));
  try {
    if (['png','jpg','jpeg','svg'].includes(file.tipo)) {
      const img = document.createElement('img'); img.onload=()=>reveal(img); img.src = file.url; img.alt = file.nome; img.className = 'preview-image'; body.replaceChildren(img);
    } else if (file.tipo === 'html') {
      const iframe = document.createElement('iframe'); iframe.src = file.url; iframe.title = file.nome; iframe.className = 'preview-frame'; iframe.setAttribute('sandbox','allow-scripts'); body.replaceChildren(iframe);
    } else if (file.tipo === 'csv') {
      const response = await fetch(file.url+'?preview', {signal:controller.signal}); if(!response.ok) throw new Error('Arquivo indisponível.'); const data = await response.json();
      if(request!==state.preview) return;
      body.innerHTML = `<p class="small muted" style="margin-bottom:12px">${data.limitado ? 'Prévia de até 200 registros. Baixe o CSV para consultar todos os dados.' : 'Todos os registros deste arquivo.'}</p><div class="table-wrap"><table class="data-table">${data.linhas.map((row,i)=>`<${i?'tbody':'thead'}><tr>${row.map(cell=>`<${i?'td':'th'}>${escape(cell)}</${i?'td':'th'}>`).join('')}</tr></${i?'tbody':'thead'}>`).join('')}</table></div>`;
    } else {
      const response = await fetch(file.url, {signal:controller.signal}); if(!response.ok) throw new Error('Arquivo indisponível.'); let text = await response.text();
      if(request!==state.preview) return;
      if(file.tipo==='json') {try{text=JSON.stringify(JSON.parse(text),null,2);}catch{}}
      body.innerHTML = `<article class="document">${file.tipo === 'md' ? markdown(text) : '<pre>'+escape(text)+'</pre>'}</article>`;
    }
    if(request===state.preview)reveal(body);
  } catch(e) { if(request===state.preview && e.name!=='AbortError') body.innerHTML='<p class="notice">'+escape(e.message)+'</p>'; }
}
async function openLibrary() {
  const version = ++selectionVersion;
  try {
    const files = await api('/api/biblioteca');
    if(version!==selectionVersion)return;
    state.library = files; state.selected = 'biblioteca'; state.detail=null; state.tab='results'; renderHistory(); renderResult(); scrollToSection('#results-section');
  }
  catch(e){toast(e.message,true);}
}
async function refresh() {
  if(state.polling) return;
  state.polling=true;
  try {
    state.jobs=await api('/api/execucoes');
    const queued=state.jobs.filter(j=>j.status==='fila').length, running=state.jobs.some(j=>j.status==='executando');
    updateText($('#queue-status'),running ? `1 em execução${queued ? ` · ${queued} na fila` : ''}` : queued ? `${queued} na fila` : 'Nenhuma execução');
    $('#queue-status').classList.toggle('is-running',running);
    if(state.selected && state.selected!=='biblioteca') {
      const selected=state.selected, version=selectionVersion; const detail=await api('/api/execucoes/'+selected);
      if(selected===state.selected && version===selectionVersion) state.detail=detail;
    }
    renderHistory(); renderResult();
    if($('#connection').textContent!=='Ambiente conectado')$('#connection').innerHTML='<span class="live-dot"></span>Ambiente conectado';
  } finally {state.polling=false;}
}
async function boot() {
  hydrateIcons();
  ['.topbar','.hero','.stats'].forEach((selector,i)=>reveal($(selector),i*45));
  try {
    state.catalogo=await api('/api/catalogo'); renderNavigation(); renderCards();
    $('#group-count').textContent=state.catalogo.grupos.length; $('#operation-count').textContent=state.catalogo.operacoes.length;
    $('#graph-status').textContent=state.catalogo.ambiente.grafo ? 'Disponível para uso' : 'Grafo não encontrado';
    const missing=Object.entries(state.catalogo.ambiente.dependencias).filter(([k,v])=>!v && k!=='geopandas').map(([k])=>k);
    if(missing.length){$('#environment-warning').hidden=false;$('#environment-warning').textContent=`Dependências ausentes: ${missing.join(', ')}. Instale no mesmo Python usado pelo painel: python -m pip install -r requirements.txt`;}
    await refresh();
    if(state.jobs.length && !state.selected && selectionVersion===0)await selectJob(state.jobs[0].id);
    setInterval(async()=>{try{await refresh();}catch{$('#connection').textContent='Servidor desconectado';}},1500);
  } catch(e) {$('#connection').textContent='Falha na conexão';$('#group-description').textContent='Não foi possível conectar ao servidor. Recarregue a página após iniciar python interface.py.';toast(e.message,true);}
}
$('#search').oninput=()=>{if(state.catalogo)renderCards();};
$('#suite-button').onclick=()=>{if(state.catalogo)configure([operacao('testes_todos')]);};
$('#pipeline-button').onclick=()=>{if(state.catalogo)configure([operacao('pipeline')]);};
$('#group-run').onclick=()=>{if(state.catalogo)configure(state.catalogo.operacoes.filter(o=>o.grupo===state.grupo && o.batch!==false));};
$('#library-button').onclick=openLibrary; $('#empty-library').onclick=openLibrary;
$('#history-button').onclick=()=>scrollToSection('#results-section');
$('#close-config').onclick=()=>closeDialog($('#config-dialog'));
$('#close-preview').onclick=()=>closeDialog($('#preview-dialog'));
$('#close-explanation').onclick=()=>closeDialog($('#explanation-dialog'));
$('#explanation-done').onclick=()=>closeDialog($('#explanation-dialog'));
document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('cancel',event=>{
  event.preventDefault(); closeDialog(dialog);
}));
for(const tab of ['results','log','params']) $('#tab-'+tab).onclick=()=>setTab(tab);
$('.result-tabs').onkeydown=event=>{if(!['ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();const tabs=[...$('.result-tabs').querySelectorAll('button:not(:disabled)')];const index=tabs.indexOf(document.activeElement);const next=tabs[(index+(event.key==='ArrowRight'?1:tabs.length-1))%tabs.length];next.focus();next.click();};
boot();
