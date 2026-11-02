import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ScanFace, Users, History, Camera, RefreshCw, CheckCircle2, ArrowRight, LogIn, LogOut, Coffee, Play, Clock3, X, Upload, ShieldCheck } from 'lucide-react';
import './style.css';

const TYPES = { entrada: 'Entrada', intervalo: 'Intervalo', retorno: 'Retorno', saida: 'Saída' };
const icons = { entrada: LogIn, intervalo: Coffee, retorno: Play, saida: LogOut };
const dateTime = value => new Date(value).toLocaleString('pt-BR', { timeZone: 'America/Araguaina' });
const localDay = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Araguaina' }).format(new Date());
async function api(path, options) {
  const response = await fetch(`/api${path}`, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a operação.');
  return data;
}

function PhotoCapture({ onPhoto, disabled, allowUpload = false }) {
  const video = useRef(null), stream = useRef(null), generation = useRef(0);
  const [active, setActive] = useState(false), [preview, setPreview] = useState(''), [error, setError] = useState('');
  function stop() { stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; }
  useEffect(() => () => { generation.current++; stop(); }, []);
  useEffect(() => { if (active && video.current) video.current.srcObject = stream.current; }, [active]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  async function start() {
    const attempt = ++generation.current;
    setError(''); onPhoto(null); setPreview(''); stop(); setActive(false);
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('A câmera requer localhost ou HTTPS.');
      const media = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      if (generation.current !== attempt) { media.getTracks().forEach(t => t.stop()); return; }
      stream.current = media; setActive(true);
    } catch (e) { setError(e.name === 'NotAllowedError' ? 'Permita o acesso à câmera no navegador.' : e.name === 'NotFoundError' ? 'Nenhuma câmera encontrada neste dispositivo.' : e.message); }
  }
  function capture() {
    if (!video.current?.videoWidth) { setError('Aguarde a câmera iniciar.'); return; }
    const canvas = document.createElement('canvas');
    canvas.width = video.current.videoWidth; canvas.height = video.current.videoHeight;
    canvas.getContext('2d').drawImage(video.current, 0, 0);
    canvas.toBlob(blob => { if (!blob) return; onPhoto(blob); setPreview(URL.createObjectURL(blob)); stop(); setActive(false); }, 'image/jpeg', .92);
  }
  function upload(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { setError('Selecione uma foto de até 5 MB.'); return; }
    generation.current++; stop(); setActive(false); setError(''); onPhoto(file); setPreview(URL.createObjectURL(file));
  }
  return <div className="photo-capture">
    <div className={`camera ${preview || active ? 'has-image' : ''}`}>
      {preview ? <img src={preview} alt="Fotografia capturada para reconhecimento"/> : active ? <video ref={video} autoPlay muted playsInline/> : <div className="camera-empty"><div className="face-symbol"><ScanFace size={62} strokeWidth={1}/></div><h3>Seu rosto é a sua identificação</h3><p>Ative a câmera e posicione seu rosto<br/>no centro da imagem.</p></div>}
      {active && <div className="face-guide" aria-hidden="true"/>}
      <span className="camera-label"><span className={active ? 'live-dot' : 'dot'}/>{active ? 'Câmera ao vivo' : preview ? 'Foto pronta para envio' : 'Câmera desativada'}</span>
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="capture-actions"><button type="button" className="secondary" disabled={disabled} onClick={active ? capture : start}>{active ? <Camera size={18}/> : preview ? <RefreshCw size={18}/> : <Camera size={18}/>} {active ? 'Capturar foto' : preview ? 'Tirar outra foto' : 'Ativar câmera'}</button>
      {allowUpload && <label className={`upload ${disabled ? 'disabled' : ''}`}><Upload size={17}/> Enviar foto<input type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} disabled={disabled}/></label>}
    </div>
  </div>;
}

function App() {
  const [page, setPage] = useState('ponto'), [employees, setEmployees] = useState([]), [records, setRecords] = useState([]);
  const [photo, setPhoto] = useState(null), [kind, setKind] = useState('entrada'), [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null), [captureKey, setCaptureKey] = useState(0), [clock, setClock] = useState(new Date());
  const [filter, setFilter] = useState(localDay), [search, setSearch] = useState(''), [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', registration: '', role: '' });
  async function refresh() {
    try { const [people, punches] = await Promise.all([api('/employees'), api('/punches')]); setEmployees(people); setRecords(punches); }
    catch (e) { setNotice({ type: 'error', text: `Falha ao carregar dados: ${e.message}` }); }
    finally { setLoading(false); }
  }
  useEffect(() => { refresh(); const timer = setInterval(() => setClock(new Date()), 1000); return () => clearInterval(timer); }, []);
  function navigate(next) { setPage(next); setPhoto(null); setNotice(null); setCaptureKey(k => k + 1); setSearch(''); }
  async function submit(event) {
    event.preventDefault(); if (!photo || busy) return;
    setBusy(true); setNotice(null);
    const payload = new FormData(); payload.append('photo', photo, 'rosto.jpg');
    if (page === 'cadastro') Object.entries(form).forEach(([key, value]) => payload.append(key, value));
    else payload.append('kind', kind);
    try {
      const result = await api(page === 'cadastro' ? '/employees' : '/punches', { method: 'POST', body: payload });
      setNotice({ type: 'success', text: page === 'cadastro' ? `${result.name} cadastrado com sucesso!` : `${TYPES[result.kind]} registrada para ${result.employee.name} em ${dateTime(result.occurred_at)}.` });
      setPhoto(null); setCaptureKey(k => k + 1); setForm({ name: '', registration: '', role: '' }); await refresh();
    } catch (e) { setNotice({ type: 'error', text: e.message }); }
    finally { setBusy(false); }
  }
  const today = localDay(), todayRecords = records.filter(r => r.occurred_at.startsWith(today));
  const visible = records.filter(r => (!filter || r.occurred_at.startsWith(filter)) && `${r.name} ${r.registration}`.toLowerCase().includes(search.toLowerCase()));
  const titles = { ponto: ['Vamos registrar seu ponto?', 'Um olhar, e tudo pronto. Registre sua jornada com reconhecimento facial.'], cadastro: ['Pessoas que fazem parte.', 'Cadastre os dados e uma fotografia para identificar cada funcionário.'], historico: ['Cada jornada, registrada.', 'Consulte os registros de entrada, intervalo, retorno e saída.'] };
  function table(items) { return <div className="table-wrap"><table><thead><tr><th>Funcionário</th><th>Matrícula</th><th>Registro</th><th>Data e horário</th></tr></thead><tbody>{items.map(r => <tr key={r.id}><td><strong>{r.name}</strong><small>{r.role}</small></td><td>{r.registration}</td><td><span className={`badge ${r.kind}`}>{TYPES[r.kind]}</span></td><td>{dateTime(r.occurred_at)}</td></tr>)}</tbody></table>{items.length === 0 && <div className="empty"><History size={28}/><p>{loading ? 'Carregando registros…' : 'Nenhum registro encontrado.'}</p></div>}</div>; }
  return <div className="shell">
    <aside><a className="brand" href="#" onClick={e => { e.preventDefault(); if (!busy) navigate('ponto'); }}><span><ScanFace/></span>Ponto<span className="brand-light">Face</span></a><div className="workspace-label">GESTÃO DE JORNADA</div>
      <nav>{[['ponto', ScanFace, 'Registrar ponto'], ['cadastro', Users, 'Funcionários'], ['historico', History, 'Histórico de pontos']].map(([id, Icon, label]) => <button disabled={busy} key={id} className={page === id ? 'selected' : ''} onClick={() => navigate(id)}><Icon size={20}/>{label}{page === id && <span className="nav-dot"/>}</button>)}</nav>
      <div className="sidebar-bottom"><ShieldCheck size={22}/><strong>Tecnologia que simplifica.</strong><p>Reconhecimento facial para acompanhar sua jornada.</p><span>PROJETO ACADÊMICO · 2026</span></div>
    </aside>
    <main><header><span>Painel de controle <span className="breadcrumb">/ {page === 'ponto' ? 'Registro de ponto' : page === 'cadastro' ? 'Funcionários' : 'Histórico'}</span></span><span className="local-chip"><span className="live-dot"/> Ambiente local</span></header>
      <div className="content"><div className="heading"><div><div className="eyebrow">PONTOFACE / {page === 'ponto' ? 'RECONHECIMENTO FACIAL' : 'GESTÃO'}</div><h1>{titles[page][0]}</h1><p>{titles[page][1]}</p></div><div className="date-card"><Clock3 size={18}/><div><strong>{clock.toLocaleTimeString('pt-BR', { timeZone: 'America/Araguaina' })}</strong><small>{clock.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', timeZone: 'America/Araguaina' })}</small></div></div></div>
      {notice && <div role={notice.type === 'error' ? 'alert' : 'status'} className={`notice ${notice.type}`}><span>{notice.type === 'success' && <CheckCircle2 size={20}/>} {notice.text}</span><button aria-label="Fechar mensagem" onClick={() => setNotice(null)}><X size={18}/></button></div>}
      <div className="stats"><div><span>Funcionários cadastrados</span><strong>{loading ? '—' : employees.length.toString().padStart(2, '0')}</strong><Users/></div><div><span>Registros de hoje</span><strong>{loading ? '—' : todayRecords.length.toString().padStart(2, '0')}</strong><Clock3/></div><div><span>Identificação</span><strong className="stat-text">Reconhecimento facial</strong><ScanFace/></div></div>
      {page !== 'historico' ? <form onSubmit={submit} className="work-grid"><section className="panel camera-panel"><div className="panel-heading"><span className="step">01</span><div><h2>{page === 'cadastro' ? 'Fotografia do funcionário' : 'Captura facial'}</h2><p>Boa iluminação faz toda a diferença.</p></div></div><PhotoCapture key={captureKey} onPhoto={setPhoto} disabled={busy} allowUpload={page === 'cadastro'}/><p className="photo-tip"><ShieldCheck size={16}/>{page === 'cadastro' ? 'A foto será armazenada para identificação facial.' : 'A captura do ponto é processada e não é armazenada.'}</p></section>
      <section className="panel details-panel"><div className="panel-heading"><span className="step">02</span><div><h2>{page === 'cadastro' ? 'Dados do funcionário' : 'Tipo de registro'}</h2><p>{page === 'cadastro' ? 'Preencha os campos abaixo.' : 'Selecione o momento da sua jornada.'}</p></div></div>
      {page === 'cadastro' ? <div className="fields">{[['name', 'Nome completo', 'Ex.: Ana Souza', 120], ['registration', 'Matrícula', 'Ex.: 2026001', 40], ['role', 'Cargo', 'Ex.: Analista de sistemas', 100]].map(([key, label, placeholder, max]) => <label key={key}>{label}<input required maxLength={max} value={form[key]} disabled={busy} placeholder={placeholder} onChange={e => setForm({ ...form, [key]: e.target.value })}/></label>)}</div> : <div className="type-options" role="radiogroup" aria-label="Tipo de registro">{Object.entries(TYPES).map(([value, label]) => { const Icon = icons[value]; return <label key={value} className={kind === value ? 'type selected-type' : 'type'}><input type="radio" name="kind" value={value} checked={kind === value} onChange={() => setKind(value)} disabled={busy}/><Icon size={22}/><span><strong>{label}</strong><small>{{ entrada: 'Começar a jornada', intervalo: 'Fazer uma pausa', retorno: 'Voltar do intervalo', saida: 'Encerrar a jornada' }[value]}</small></span><span className="radio-dot"/></label>; })}</div>}
      <button className="primary" type="submit" disabled={!photo || busy}>{busy ? 'Processando reconhecimento…' : page === 'cadastro' ? 'Cadastrar funcionário' : 'Confirmar e registrar ponto'}{!busy && <ArrowRight size={18}/>}</button><p className="submit-tip">{busy ? 'O primeiro uso pode demorar para baixar e carregar o modelo.' : !photo ? 'Capture uma foto para continuar.' : 'Foto pronta. Você já pode confirmar.'}</p></section></form> : <section className="panel"><div className="panel-heading history-heading"><div><h2>Histórico de registros</h2><p>{visible.length} registro(s) encontrado(s)</p></div><div className="filters"><label>Data<input type="date" value={filter} onChange={e => setFilter(e.target.value)}/></label><label>Funcionário<input placeholder="Nome ou matrícula" value={search} onChange={e => setSearch(e.target.value)}/></label><button type="button" className="secondary" onClick={() => { setFilter(''); setSearch(''); }}>Limpar</button><button type="button" className="icon-button" aria-label="Atualizar registros" onClick={refresh}><RefreshCw size={18}/></button></div></div>{table(visible)}</section>}
      {page === 'ponto' && <section className="panel recent"><div className="panel-heading"><div><h2>Últimos registros</h2><p>As movimentações mais recentes da equipe.</p></div><button disabled={busy} className="text-button" onClick={() => navigate('historico')}>Ver histórico <ArrowRight size={16}/></button></div>{table(records.slice(0, 5))}</section>}
      {page === 'cadastro' && <section className="panel recent"><div className="panel-heading"><div><h2>Funcionários cadastrados</h2><p>{employees.length} pessoa(s) na equipe</p></div></div><div className="people">{employees.map(e => <article key={e.id}><img src={`/api/employees/${e.id}/photo`} alt={`Foto de ${e.name}`}/><div><strong>{e.name}</strong><small>{e.role} · {e.registration}</small></div><span className="badge entrada">Cadastrado</span></article>)}{!employees.length && <p className="empty">Cadastre o primeiro funcionário para começar.</p>}</div></section>}
      <footer><span>PontoFace · Sistema de registro de ponto</span><span>React + Python + DeepFace</span></footer></div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
