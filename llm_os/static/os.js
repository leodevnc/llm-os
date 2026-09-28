function renderOS(state) {
  $('file-count').textContent=state.files.length;
  $('os-disk-count').textContent=state.files.length+' versioned files on disk';
  $('os-model-status').textContent=models.length?'Local Ollama · '+models.join(', '):'Local model offline · scripted programs available';
  $('os-apps').replaceChildren();
  for(const app of state.apps){
    const card=node('article',undefined,'app-card');
    card.append(node('span',app.write_roots.length?'REVIEWED WRITES':'READ ONLY','app-permission'),node('h3',app.name),node('p',app.description));
    const tools=node('div',undefined,'tool-tags');
    for(const name of app.tools)tools.append(node('span',name));
    card.append(tools,node('small',app.write_roots.length?'Write scope: '+app.write_roots.join(', '):'No writable directories'));
    const launch=node('button','Open app →','subtle');
    launch.onclick=()=>{view('tasks');$('mode').value='ollama';modeChanged();$('app-id').value=app.id;$('goal').focus();if(!models.length)notify('This app needs an installed local Ollama model. The Computer view offers the scripted OS demo.');};
    card.append(launch);$('os-apps').append(card);
  }
  $('os-processes').replaceChildren();
  for(const task of state.tasks){const button=node('button',undefined,'process-row');button.append(node('span',task.goal),node('small',task.steps+'/'+task.max_steps+' turns'),node('strong',task.state,'state-'+task.state));button.onclick=()=>select(task.id).catch(e=>notify(e.message));$('os-processes').append(button);}
  if(!state.tasks.length)$('os-processes').append(node('p','No processes yet. Run the OS demo to inspect the complete loop.','placeholder'));
  $('os-files').replaceChildren();
  for(const file of state.files){const card=node('article',undefined,'document-card');card.append(node('small','VIRTUAL FILE · VERSION '+file.version),node('h3',file.path),node('pre',file.content));$('os-files').append(card);}
  if(!state.files.length)$('os-files').append(node('p','No files on disk yet. An approved fs_write creates a file here.','placeholder'));
}

function renderRAM(task) {
  const ram=task.working_memory;
  const panel=$('working-memory');panel.replaceChildren();
  const header=node('div',undefined,'ram-heading');header.append(node('strong','Working memory'),node('span',ram.used_chars.toLocaleString()+' / '+ram.budget_chars.toLocaleString()+' source characters'));
  const meter=node('meter');meter.min=0;meter.max=ram.budget_chars;meter.value=ram.used_chars;meter.setAttribute('aria-label','Resident source characters');
  panel.append(header,meter);
  const pages=node('div',undefined,'resident-pages');
  for(const page of ram.pages)pages.append(node('span',page.title+' · '+page.chars+' chars'));
  if(!ram.pages.length)pages.append(node('small','No source pages resident. Backing documents remain on disk.'));
  panel.append(pages,node('small','App: '+task.app.name+' · '+task.app.tools.length+' allowed tools'));
}

$('run-os-demo').onclick=()=>{view('tasks');$('mode').value='os-demo';modeChanged();$('task-form').requestSubmit();};
