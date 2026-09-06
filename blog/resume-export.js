(function(){
  'use strict';
  const DEFAULTS={previewSelector:'#resume-preview',buttonSelector:'[data-export-pdf]',statusSelector:'[data-export-status]',nameSelector:'[data-resume-name]',pageSize:'letter'};
  function slugifyName(value){return (value||'resume').trim().replace(/[^a-z0-9]+/gi,'-').replace(/^-+|-+$/g,'').toLowerCase()||'resume'}
  function getResumeFileName(name){const stamp=new Date().toISOString().slice(0,10);return `${slugifyName(name)}-resume-${stamp}.pdf`}
  function setStatus(node,message,type){if(!node)return;node.textContent=message||'';node.dataset.state=type||'idle'}
  function setExporting(root,isExporting){root.classList.toggle('is-exporting',isExporting);document.body.classList.toggle('is-exporting',isExporting)}
  function beforePrint(root){setExporting(root,true)}
  function afterPrint(root,button,status,successMessage){setExporting(root,false);if(button){button.disabled=false;button.removeAttribute('aria-busy')}setStatus(status,successMessage||'Print dialog opened. Choose “Save as PDF” to download.', 'success')}
  async function exportWithHtml2Pdf(preview,filename,pageSize){
    if(!window.html2pdf) return false;
    const options={margin:0.5,filename,image:{type:'jpeg',quality:0.98},html2canvas:{scale:2,useCORS:true,backgroundColor:'#ffffff',logging:false},jsPDF:{unit:'in',format:pageSize==='a4'?'a4':'letter',orientation:'portrait'},pagebreak:{mode:['css','legacy'],avoid:['.resume-section','.resume-item','.resume-header']}};
    await window.html2pdf().set(options).from(preview).save();
    return true;
  }
  async function exportToPDF(options={}){
    const config=Object.assign({},DEFAULTS,options);const root=config.root||document;const preview=root.querySelector(config.previewSelector);const button=root.querySelector(config.buttonSelector);const status=root.querySelector(config.statusSelector);const nameInput=root.querySelector(config.nameSelector);const pageSize=(root.querySelector('[data-page-size]')?.value||config.pageSize||'letter').toLowerCase();
    if(!preview){setStatus(status,'Export failed: resume preview was not found.','error');throw new Error('Missing resume preview container')}
    const filename=getResumeFileName(nameInput&&nameInput.value);preview.dataset.pdfFilename=filename;if(button){button.disabled=true;button.setAttribute('aria-busy','true')}setStatus(status,`Preparing ${filename}…`,'loading');setExporting(root,true);
    try{
      if(window.html2pdf){await exportWithHtml2Pdf(preview,filename,pageSize);afterPrint(root,button,status,`Downloaded ${filename}.`);return {method:'html2pdf',filename}}
      const onAfter=()=>{window.removeEventListener('afterprint',onAfter);afterPrint(root,button,status)};window.addEventListener('afterprint',onAfter,{once:true});setTimeout(()=>window.print(),80);setTimeout(()=>{if(button&&button.disabled)afterPrint(root,button,status,'If no print dialog appeared, allow pop-ups/printing and try again.')},3000);return {method:'native-print',filename};
    }catch(error){setExporting(root,false);if(button){button.disabled=false;button.removeAttribute('aria-busy')}setStatus(status,'PDF export failed. Use your browser menu: File → Print → Save as PDF.','error');throw error}
  }
  function bindResumeExport(options={}){const root=options.root||document;const button=root.querySelector(options.buttonSelector||DEFAULTS.buttonSelector);if(!button)return null;button.addEventListener('click',()=>exportToPDF(options).catch(console.error));window.addEventListener('beforeprint',()=>beforePrint(root));return {exportToPDF}}
  window.ClearGlassResumeExport={exportToPDF,bindResumeExport,getResumeFileName};
})();
