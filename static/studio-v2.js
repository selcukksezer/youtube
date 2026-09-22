(() => {
  const $ = (id) => document.getElementById(id);
  let project = null;
  let job = null;
  const setStage = (name, title, copy) => {
    document.querySelectorAll('.stage').forEach((el) => el.classList.add('hidden'));
    $(`${name}-stage`).classList.remove('hidden');
    $('stage-title').textContent = title;
    $('stage-copy').textContent = copy;
    document.querySelectorAll('.rail-step').forEach((el) => el.classList.toggle('active', el.dataset.step === name));
  };
  const api = async (url, options = {}) => {
    const response = await fetch(url, {headers: {'Content-Type': 'application/json'}, ...options});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'İşlem başarısız');
    return data;
  };
  $('start').onclick = async () => {
    const title = $('topic').value.trim();
    if (!title) return alert('Önce bir konu yazın.');
    try {
      $('start').disabled = true;
      const made = await api('/api/v2/projects', {method:'POST', body:JSON.stringify({title, niche:$('niche').value, language:$('language').value})});
      project = made.project; $('project-id').textContent = project.id; setStage('script','Senaryoyu şekillendir','Senaryoyu okuyun, gerektiğinde yenileyin ve kalite kontrolünden geçirin.');
      const generated = await api(`/api/v2/projects/${project.id}/script`, {method:'POST', body:JSON.stringify({topic:title})});
      $('script').value = generated.plan.full_narration || ''; $('script-score').textContent = generated.validation?.ok ? 'Kalite kontrolü geçti' : 'Düzenleme gerekli';
    } catch (error) { alert(error.message); } finally { $('start').disabled = false; }
  };
  $('regenerate').onclick = async () => {
    if (!project) return;
    try {
      $('regenerate').disabled = true;
      const generated = await api(`/api/v2/projects/${project.id}/script`, {method:'POST', body:JSON.stringify({topic:project.title})});
      $('script').value = generated.plan.full_narration || '';
      $('script-score').textContent = generated.validation?.ok ? 'Kalite kontrolü geçti' : 'Düzenleme gerekli';
    } catch (error) { alert(error.message); } finally { $('regenerate').disabled = false; }
  };
  $('validate').onclick = async () => { try {
    const latest = await api(`/api/v2/projects/${project.id}`);
    const plan = latest.project.plan;
    if (!plan) throw new Error('Senaryo bulunamadı');
    const narration = $('script').value.trim();
    if (!narration) throw new Error('Senaryo boş olamaz');
    // The editor changes the narration source used by the render pipeline.
    // Scene-level narration stays intact to preserve timing and visual intent.
    plan.full_narration = narration;
    await api(`/api/v2/projects/${project.id}`, {method:'PATCH', body:JSON.stringify({plan})});
    const result = await api(`/api/v2/projects/${project.id}/validate`, {method:'POST'});
    if (!result.ok) return alert('Senaryo kalite kapısından geçmedi.');
    $('render-title').textContent = project.title; setStage('render','Render ayarlarını seç','Yayınlanabilir varsayılanlar hazır. İstersen ileri ayarları aç.');
  } catch (error) { alert(error.message); } };
  $('render').onclick = async () => { try { const result = await api(`/api/v2/projects/${project.id}/render`, {method:'POST',body:JSON.stringify({settings:{resolution:$('resolution').value,voice_gender:$('voice').value,split_screen:$('split').checked}})}); job = result.job; $('progress').classList.remove('hidden'); $('render').disabled = true; setStage('render','Video üretiliyor','Render tamamlanana kadar bu sekmeyi kapatabilirsiniz.'); const events = new EventSource(`/api/v2/render-jobs/${job.id}/events`); events.onmessage = (event) => { const payload = JSON.parse(event.data); const current = payload.job; if (!current) return; $('progress-step').textContent = current.step; $('progress-pct').textContent = `${current.percent}%`; $('progress-bar').style.width = `${current.percent}%`; if (current.status === 'completed') { events.close(); $('result-copy').textContent = 'Dosya hazır. Galeriden veya aşağıdaki bağlantıdan açabilirsiniz.'; $('result-link').href = current.output_url || '#'; setStage('result','Video hazır','Üretim tamamlandı.'); } if (current.status === 'failed') { events.close(); alert(current.error_message || 'Render başarısız'); $('render').disabled = false; } }; } catch (error) { alert(error.message); $('render').disabled = false; } };
  $('system-state').textContent = 'V2 Studio hazır';
})();
