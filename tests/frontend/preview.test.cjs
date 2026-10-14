// Regressões de concorrência sem navegador ou dependências npm.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../interface/static/app.js'), 'utf8').replace(/boot\(\);\s*$/, '');

function deferred() {
  let resolve; const promise = new Promise(done => resolve = done);
  return {promise, resolve};
}

function harness(fetch = async () => { throw new Error('Requisição inesperada'); }) {
  const nodes = new Map(), closeEvents = [];
  function element(id='') {
    return {
      id, open:false, hidden:false, dataset:{}, children:[], innerHTML:'', textContent:'', attrs:{},
      classList:{add(){},remove(){},toggle(){}}, listeners:{},
      addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); },
      setAttribute(key,value){this.attrs[key]=value;}, removeAttribute(key){delete this.attrs[key];},
      replaceChildren(...children){this.children=children;this.innerHTML='';},
      querySelector(){return element();}, querySelectorAll(){return [];},
      getBoundingClientRect(){return {height:240,left:0,top:0};},
      showModal(){this.open=true;},
      close(){this.open=false;closeEvents.push(()=>this.listeners.close?.forEach(fn=>fn()));},
    };
  }
  const node = selector => {
    if(!nodes.has(selector))nodes.set(selector,element(selector.slice(1)));
    return nodes.get(selector);
  };
  const document = {
    querySelector: selector => selector === 'dialog[open]' ? [...nodes.values()].find(n=>n.open) : node(selector),
    querySelectorAll: selector => selector === 'dialog' ? [node('#config-dialog'),node('#preview-dialog')] : [],
    createElement: tag => element(tag),
  };
  const context = vm.createContext({document, fetch, AbortController, console, setTimeout, clearTimeout,
    matchMedia:()=>({matches:true,addEventListener(){}}),
    IntersectionObserver:class {observe(){} unobserve(){}},
  });
  vm.runInContext(source,context);
  return {node, closeEvents, run:code=>vm.runInContext(code,context), context};
}

test('fechamento atrasado de A não apaga o mapa B nem impede reabrir A', async()=>{
  const h=harness();
  await h.run("preview({nome:'mapa.html',tipo:'html',url:'/mapa-a.html'})");
  await h.run("closeDialog(document.querySelector('#preview-dialog'))");
  await h.run("preview({nome:'mapa.html',tipo:'html',url:'/mapa-b.html'})");
  h.closeEvents.splice(0).forEach(deliver=>deliver());
  assert.equal(h.node('#preview-dialog').open,true);
  assert.equal(h.node('#preview-body').children[0]?.src,'/mapa-b.html');
  await h.run("closeDialog(document.querySelector('#preview-dialog'))");
  await h.run("preview({nome:'mapa.html',tipo:'html',url:'/mapa-a.html'})");
  h.closeEvents.splice(0).forEach(deliver=>deliver());
  assert.equal(h.node('#preview-body').children[0]?.src,'/mapa-a.html');
});

test('arquivo que termina de carregar depois do fechamento não substitui o novo mapa', async()=>{
  const response=deferred(); let signal;
  const h=harness((url,options)=>{signal=options.signal;return response.promise;});
  const loading=h.run("preview({nome:'dados.csv',tipo:'csv',url:'/dados.csv'})");
  await h.run("closeDialog(document.querySelector('#preview-dialog'))");
  assert.equal(signal.aborted,true);
  await h.run("preview({nome:'mapa.html',tipo:'html',url:'/mapa.html'})");
  response.resolve({ok:true,json:async()=>({linhas:[['antigo']],limitado:false})});
  await loading;
  assert.equal(h.node('#preview-body').children[0]?.src,'/mapa.html');
});

test('seleção durante polling carrega imediatamente a execução escolhida', async()=>{
  const response=deferred(), requests=[];
  const h=harness(url=>{requests.push(url);return response.promise;});
  h.run("renderHistory=()=>{}; renderResult=()=>{}; state.polling=true; state.jobs=[{id:'b',status:'concluido'}];");
  const selection=h.run("selectJob('b')");
  assert.deepEqual(requests,['/api/execucoes/b']);
  response.resolve({ok:true,json:async()=>({id:'b',artefatos:[]})});
  await selection;
  assert.equal(h.run('state.detail.id'),'b');
});

test('alternar A → B → A ignora respostas antigas mesmo com o mesmo id', async()=>{
  const responses=[];
  const h=harness(()=>{const response=deferred();responses.push(response);return response.promise;});
  h.run("renderHistory=()=>{}; renderResult=()=>{}; state.jobs=[{id:'a',status:'concluido'},{id:'b',status:'concluido'}];");
  const first=h.run("selectJob('a')"), second=h.run("selectJob('b')"), last=h.run("selectJob('a')");
  responses[2].resolve({ok:true,json:async()=>({id:'a',versao:'nova'})});await last;
  responses[0].resolve({ok:true,json:async()=>({id:'a',versao:'antiga'})});await first;
  responses[1].resolve({ok:true,json:async()=>({id:'b'})});await second;
  assert.equal(h.run('state.detail.id'),'a');
  assert.equal(h.run('state.detail.versao'),'nova');
});

test('cartão de outro teste não permanece clicável enquanto a nova seleção carrega',()=>{
  const h=harness();
  h.node('#result-content').innerHTML='<button>mapa antigo</button>';
  h.run("state.selected='b'; state.detail=null; state.jobs=[{id:'b',nome:'Mapa B'}]; renderResult();");
  assert.equal(h.node('#result-content').attrs['aria-busy'],'true');
  assert.ok(!h.node('#result-content').innerHTML.includes('mapa antigo'));
});
