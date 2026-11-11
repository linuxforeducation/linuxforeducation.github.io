(function(){
  var b=document.querySelector('.menu-btn'),n=document.getElementById('meniu');
  if(b&&n)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  var list=document.getElementById('lista');if(!list)return;
  var posts=[].slice.call(list.querySelectorAll('.post')),btn=document.getElementById('mai-multe'),
      inp=document.getElementById('filtru'),none=document.getElementById('nimic'),STEP=20,limit=STEP;
  function fold(s){return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')}
  var idx=posts.map(function(p){return fold(p.querySelector('summary').textContent)});
  function render(){
    var q=fold(inp.value.trim()),shown=0,match=0;
    posts.forEach(function(p,i){
      var ok=!q||idx[i].indexOf(q)>-1; if(ok)match++;
      var vis=ok&&(q||match<=limit); p.hidden=!vis; if(vis)shown++;
    });
    none.hidden=match>0;
    var left=match-shown; btn.hidden=left<=0;
    btn.textContent='Arată mai multe ('+left+' rămase)';
  }
  btn.addEventListener('click',function(){limit+=STEP;render()});
  inp.addEventListener('input',render);
  function openHash(){
    var id=decodeURIComponent(location.hash.slice(1));if(!id)return;
    var el=document.getElementById(id);if(!el||!el.classList.contains('post'))return;
    limit=Math.max(limit,posts.indexOf(el)+1);render();
    el.querySelector('details').open=true;el.scrollIntoView();
  }
  render();openHash();window.addEventListener('hashchange',openHash);
})();
