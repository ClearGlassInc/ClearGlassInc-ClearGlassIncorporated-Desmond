(function(){
  'use strict';
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cards=document.querySelectorAll('.tech-card,.product-card,.command-panel,.ops-card,.value-card');
  cards.forEach(function(card){
    card.classList.add('artemis-instrumented');
    var corner=document.createElement('span');
    corner.className='artemis-corner';
    corner.setAttribute('aria-hidden','true');
    card.appendChild(corner);
    if(!reduce){card.addEventListener('pointermove',function(event){
      var bounds=card.getBoundingClientRect();
      card.style.setProperty('--mx',(event.clientX-bounds.left)+'px');
      card.style.setProperty('--my',(event.clientY-bounds.top)+'px');
    },{passive:true});}
  });
  var toggle=document.querySelector('.artemis-toggle');
  if(toggle){toggle.addEventListener('click',function(){
    var active=toggle.getAttribute('aria-pressed')==='true';
    toggle.setAttribute('aria-pressed',String(!active));
    toggle.classList.toggle('is-active',!active);
    document.documentElement.classList.toggle('artemis-telemetry-off',active);
  });}
})();
